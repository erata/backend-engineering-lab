package de.backendlab.ee;

import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import jakarta.annotation.Resource;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.json.bind.Jsonb;
import jakarta.json.bind.JsonbBuilder;
import jakarta.ws.rs.BadRequestException;
import jakarta.ws.rs.DefaultValue;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.NotFoundException;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.PathParam;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.QueryParam;
import jakarta.ws.rs.core.MediaType;

import java.sql.SQLException;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;
import javax.sql.DataSource;

import redis.clients.jedis.ConnectionPoolConfig;
import redis.clients.jedis.DefaultJedisClientConfig;
import redis.clients.jedis.RedisClient;
import redis.clients.jedis.exceptions.JedisException;
import redis.clients.jedis.params.SetParams;

/**
 * Lab 08 on WildFly: Redis as a shared cache with <b>Jedis</b>, a client that borrows one connection per command from
 * a pool (Spring's Lettuce and .NET's StackExchange.Redis multiplex all requests over one connection).
 * Same contract as the other ports: cache-aside on {@code lab:product:{id}}, MySQL + 100 ms on a miss, 30 s TTL,
 * {@code lab:loads:{id}} counts loads across instances, modes none | local | distributed ({@code SET NX PX} lock).
 * <ul>
 *   <li>Connect and socket timeouts are 500 ms, like the other ports (Jedis default is 2 s).</li>
 *   <li>Pool size {@code REDIS_POOL_MAX} (default 8, the Jedis default); waiting for a free connection is bounded
 *       to 500 ms, after which the request falls back to MySQL like any other Redis failure.</li>
 * </ul>
 * The lock is released with an atomic compare-and-delete script. Remaining lab simplification: a fixed 3 s lease and
 * no fencing token.
 */
@Path("lab/redis")
@Produces(MediaType.APPLICATION_JSON)
@ApplicationScoped
public class RedisResource {

    private static final long TTL_MS = 30_000;
    private static final long LEASE_MS = 3_000;
    private static final AtomicLong FALLBACKS = new AtomicLong();
    /** Delete the lock only if it still holds this caller's token (atomic in Redis). */
    static final String RELEASE_LOCK =
            "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end";
    private static final Jsonb JSON = JsonbBuilder.create();

    @Resource(lookup = "java:app/jdbc/LabDS")
    DataSource ds;

    private final String instance = System.getenv().getOrDefault("HOSTNAME", "local");
    private final ConcurrentHashMap<String, CompletableFuture<String>> inflight = new ConcurrentHashMap<>();
    private int poolMax;
    private RedisClient redis;

    @PostConstruct
    void init() {
        // Created on first use of the bean (CDI instantiates lazily); the pool opens connections on demand, so a
        // deployment without Redis never connects.
        poolMax = Integer.parseInt(System.getenv().getOrDefault("REDIS_POOL_MAX", "8"));
        var pool = new ConnectionPoolConfig();
        pool.setMaxTotal(poolMax);
        pool.setMaxIdle(poolMax);
        pool.setMaxWait(Duration.ofMillis(500));
        redis = RedisClient.builder()
                .hostAndPort(System.getenv().getOrDefault("REDIS_HOST", "localhost"), 6379)
                .clientConfig(DefaultJedisClientConfig.builder().connectionTimeoutMillis(500).socketTimeoutMillis(500).build())
                .poolConfig(pool)
                .build();
    }

    @PreDestroy
    void close() {
        if (redis != null) {
            redis.close();
        }
    }

    private void lab() {
        if (!"true".equals(System.getenv("LAB_ENABLED"))) {
            throw new NotFoundException();
        }
    }

    @GET
    @Path("product/{id}")
    public Map<String, Object> product(@PathParam("id") long id, @DefaultValue("distributed") @QueryParam("mode") String mode)
            throws InterruptedException {
        lab();
        if (!Set.of("none", "local", "distributed").contains(mode)) {
            throw new BadRequestException("mode none|local|distributed");
        }
        long t0 = System.nanoTime();
        String key = "lab:product:" + id;
        try {
            String value = redis.get(key);
            String source = "redis";
            if (value == null) {
                source = "loaded-or-waited";
                value = switch (mode) {
                    case "none" -> load(id, key);
                    case "local" -> local(id, key);
                    default -> distributed(id, key);
                };
            }
            return Map.of("value", value, "source", source, "instance", instance, "ms", (System.nanoTime() - t0) / 1e6);
        } catch (JedisException e) {
            // Fail open, as in the other ports: serve from MySQL without caching.
            FALLBACKS.incrementAndGet();
            return Map.of("value", productJson(id, name(id)), "source", "db-fallback", "instance", instance,
                    "ms", (System.nanoTime() - t0) / 1e6, "error", e.getClass().getSimpleName());
        }
    }

    /** Serialized with JSON-B, so quotes, backslashes and control characters in product names are escaped. */
    private static String productJson(long id, String name) {
        Map<String, Object> product = new LinkedHashMap<>();
        product.put("id", id);
        product.put("name", name);
        return JSON.toJson(product);
    }

    private String name(long id) {
        try (var c = ds.getConnection(); var st = c.prepareStatement("SELECT name FROM products WHERE id=?")) {
            st.setLong(1, id);
            try (var rs = st.executeQuery()) {
                rs.next();
                return rs.getString(1);
            }
        } catch (SQLException e) {
            throw new IllegalStateException(e);
        }
    }

    private String load(long id, String key) {
        redis.incr("lab:loads:" + id);
        String value = productJson(id, name(id));
        try {
            Thread.sleep(100);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException(e);
        }
        redis.set(key, value, SetParams.setParams().px(TTL_MS));
        return value;
    }

    private String local(long id, String key) {
        var mine = new CompletableFuture<String>();
        var leader = inflight.putIfAbsent(key, mine);
        if (leader != null) {
            try {
                return leader.join();
            } catch (CompletionException e) {
                throw e.getCause() instanceof RuntimeException cause ? cause : e;
            }
        }
        try {
            String v = redis.get(key);
            if (v == null) {
                v = load(id, key);
            }
            mine.complete(v);
            return v;
        } catch (RuntimeException e) {
            mine.completeExceptionally(e);
            throw e;
        } finally {
            inflight.remove(key, mine);
        }
    }

    private String distributed(long id, String key) throws InterruptedException {
        String lock = "lab:lock:" + id;
        long deadline = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(LEASE_MS);
        while (System.nanoTime() < deadline) {
            String token = instance + "-" + UUID.randomUUID();
            if ("OK".equals(redis.set(lock, token, SetParams.setParams().nx().px(LEASE_MS)))) {
                try {
                    String v = redis.get(key);
                    return v != null ? v : load(id, key);
                } finally {
                    redis.eval(RELEASE_LOCK, List.of(lock), List.of(token));
                }
            }
            Thread.sleep(10);
            String v = redis.get(key);
            if (v != null) {
                return v;
            }
        }
        throw new IllegalStateException("lock not acquired within lease");
    }

    @POST
    @Path("invalidate")
    public Map<String, Object> invalidate(@DefaultValue("42") @QueryParam("id") long id) {
        lab();
        return Map.of("invalidated", redis.del("lab:product:" + id) > 0);
    }

    @POST
    @Path("reset")
    public Map<String, Object> reset(@DefaultValue("42") @QueryParam("id") long id) {
        lab();
        redis.del("lab:product:" + id, "lab:loads:" + id, "lab:lock:" + id);
        return Map.of("reset", id);
    }

    @GET
    @Path("loads")
    public Map<String, Object> loads(@DefaultValue("42") @QueryParam("id") long id) {
        lab();
        String v = redis.get("lab:loads:" + id);
        return Map.of("id", id, "loads", v == null ? 0 : Long.parseLong(v), "fallbacks", FALLBACKS.get(),
                "client", "Jedis", "poolMax", poolMax);
    }

    /** Lock regression check, same as Spring: a stale owner must not delete the lock of the next owner. */
    @POST
    @Path("lock-check")
    public Map<String, Object> lockCheck(@DefaultValue("42") @QueryParam("id") long id) throws InterruptedException {
        lab();
        String lock = "lab:lockcheck:" + id;
        redis.del(lock);
        redis.set(lock, "A", SetParams.setParams().nx().px(200));
        Thread.sleep(300);
        boolean bAcquired = "OK".equals(redis.set(lock, "B", SetParams.setParams().nx().px(LEASE_MS)));
        long releasedByA = ((Number) redis.eval(RELEASE_LOCK, List.of(lock), List.of("A"))).longValue();
        String holder = redis.get(lock);
        long releasedByB = ((Number) redis.eval(RELEASE_LOCK, List.of(lock), List.of("B"))).longValue();
        return Map.of("bAcquiredAfterExpiry", bAcquired, "staleOwnerDeleted", releasedByA,
                "holderAfterStaleRelease", String.valueOf(holder), "ownerDeleted", releasedByB,
                "correct", bAcquired && releasedByA == 0 && "B".equals(holder) && releasedByB == 1);
    }
}
