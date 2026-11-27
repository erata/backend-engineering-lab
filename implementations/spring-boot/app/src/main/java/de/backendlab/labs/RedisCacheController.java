package de.backendlab.labs;

import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Profile;
import org.springframework.dao.DataAccessException;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import tools.jackson.databind.ObjectMapper;

/**
 * Lab 08: Redis as a <b>shared</b> cache in front of MySQL, used by several application instances.
 * Cache-aside: read {@code lab:product:{id}}; on a miss load from MySQL (plus 100 ms to model an expensive query) and
 * store it with a 30 s TTL. Every load increments {@code lab:loads:{id}} so that stampedes can be counted across
 * instances.
 * <ul>
 *   <li>{@code none} – every request that misses loads (cross-instance stampede).</li>
 *   <li>{@code local} – in-process single-flight: at most one load per key <i>per instance</i>.</li>
 *   <li>{@code distributed} – Redis lock ({@code SET NX PX}) so that one instance loads and the others wait for the value.</li>
 * </ul>
 * The lock is released with an atomic compare-and-delete script, so an instance never deletes a lock that expired
 * and was taken by another instance. Remaining lab simplification: a fixed 3 s lease and no fencing token, so a holder
 * that is paused for longer than the lease can still overlap with the next holder.
 */
@Profile("lab")
@RestController
@RequestMapping("/lab/redis")
public class RedisCacheController {

    private static final Duration TTL = Duration.ofSeconds(30);
    private static final Duration LEASE = Duration.ofSeconds(3);
    private static final AtomicLong FALLBACKS = new AtomicLong();

    /** Delete the lock only if it still holds this caller's token (atomic in Redis). */
    static final DefaultRedisScript<Long> RELEASE_LOCK = new DefaultRedisScript<>(
            "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end", Long.class);

    private final StringRedisTemplate redis;
    private final JdbcTemplate jdbc;
    private final ObjectMapper json;
    private final String instance;
    private final ConcurrentHashMap<String, CompletableFuture<String>> inflight = new ConcurrentHashMap<>();

    public RedisCacheController(StringRedisTemplate redis, JdbcTemplate jdbc, ObjectMapper json,
                                @Value("${HOSTNAME:local}") String instance) {
        this.redis = redis;
        this.jdbc = jdbc;
        this.json = json;
        this.instance = instance;
    }

    @GetMapping("/product/{id}")
    public Map<String, Object> product(@PathVariable long id, @RequestParam(defaultValue = "distributed") String mode)
            throws InterruptedException {
        long t0 = System.nanoTime();
        try {
            return cached(id, mode, t0);
        } catch (DataAccessException e) {
            // Fail open: Redis unavailable (connection refused or 500 ms command timeout) -> serve from MySQL without
            // caching. Availability is kept, but every request now hits the database (no stampede protection either).
            FALLBACKS.incrementAndGet();
            return Map.of("value", productJson(id, name(id)), "source", "db-fallback", "instance", instance,
                    "ms", (System.nanoTime() - t0) / 1e6, "error", e.getClass().getSimpleName());
        }
    }

    private Map<String, Object> cached(long id, String mode, long t0) throws InterruptedException {
        String key = "lab:product:" + id;
        String value = redis.opsForValue().get(key);
        String source = "redis";
        if (value == null) {
            source = "loaded-or-waited";
            value = switch (mode) {
                case "none" -> load(id, key);
                case "local" -> local(id, key);
                case "distributed" -> distributed(id, key);
                default -> throw new IllegalArgumentException("mode none|local|distributed");
            };
        }
        return Map.of("value", value, "source", source, "instance", instance, "ms", (System.nanoTime() - t0) / 1e6);
    }

    private String name(long id) {
        return jdbc.queryForObject("SELECT name FROM products WHERE id=?", String.class, id);
    }

    /** Serialized with Jackson, so quotes, backslashes and control characters in product names are escaped. */
    private String productJson(long id, String name) {
        Map<String, Object> product = new LinkedHashMap<>();
        product.put("id", id);
        product.put("name", name);
        return json.writeValueAsString(product);
    }

    private String load(long id, String key) {
        redis.opsForValue().increment("lab:loads:" + id);
        String value = productJson(id, name(id));
        try {
            Thread.sleep(100);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException(e);
        }
        redis.opsForValue().set(key, value, TTL);
        return value;
    }

    private String local(long id, String key) {
        var mine = new CompletableFuture<String>();
        var leader = inflight.putIfAbsent(key, mine);
        if (leader != null) {
            try {
                return leader.join();
            } catch (CompletionException e) {
                // Rethrow the leader's own exception (e.g. a Redis DataAccessException) so that followers take the
                // same fail-open path as the leader instead of failing with a wrapped exception.
                if (e.getCause() instanceof RuntimeException cause) {
                    throw cause;
                }
                throw e;
            }
        }
        try {
            String v = redis.opsForValue().get(key);
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
        long deadline = System.nanoTime() + LEASE.toNanos();
        while (System.nanoTime() < deadline) {
            String token = instance + "-" + UUID.randomUUID();
            if (Boolean.TRUE.equals(redis.opsForValue().setIfAbsent(lock, token, LEASE))) {
                try {
                    String v = redis.opsForValue().get(key);
                    return v != null ? v : load(id, key);
                } finally {
                    redis.execute(RELEASE_LOCK, List.of(lock), token);
                }
            }
            Thread.sleep(10);
            String v = redis.opsForValue().get(key);
            if (v != null) {
                return v;
            }
        }
        throw new IllegalStateException("lock not acquired within lease");
    }

    /** Explicit invalidation after a write; without it other instances serve the old value until the 30 s TTL expires. */
    @PostMapping("/invalidate")
    public Map<String, Object> invalidate(@RequestParam(defaultValue = "42") long id) {
        return Map.of("invalidated", Boolean.TRUE.equals(redis.delete("lab:product:" + id)));
    }

    @PostMapping("/reset")
    public Map<String, Object> reset(@RequestParam(defaultValue = "42") long id) {
        redis.delete(List.of("lab:product:" + id, "lab:loads:" + id, "lab:lock:" + id));
        return Map.of("reset", id);
    }

    @GetMapping("/loads")
    public Map<String, Object> loads(@RequestParam(defaultValue = "42") long id) {
        String v = redis.opsForValue().get("lab:loads:" + id);
        return Map.of("id", id, "loads", v == null ? 0 : Long.parseLong(v), "fallbacks", FALLBACKS.get(),
                "client", "Lettuce", "disconnected", System.getenv().getOrDefault("LAB_REDIS_DISCONNECTED", "default"));
    }

    /**
     * Lock regression check: take the lock with token A, let it expire, let token B take it, then release with A.
     * An atomic compare-and-delete must leave B's lock in place.
     */
    @PostMapping("/lock-check")
    public Map<String, Object> lockCheck(@RequestParam(defaultValue = "42") long id) throws InterruptedException {
        String lock = "lab:lockcheck:" + id;
        redis.delete(lock);
        redis.opsForValue().setIfAbsent(lock, "A", Duration.ofMillis(200));
        Thread.sleep(300);
        boolean bAcquired = Boolean.TRUE.equals(redis.opsForValue().setIfAbsent(lock, "B", LEASE));
        Long releasedByA = redis.execute(RELEASE_LOCK, List.of(lock), "A");
        String holder = redis.opsForValue().get(lock);
        Long releasedByB = redis.execute(RELEASE_LOCK, List.of(lock), "B");
        return Map.of("bAcquiredAfterExpiry", bAcquired, "staleOwnerDeleted", releasedByA, "holderAfterStaleRelease",
                String.valueOf(holder), "ownerDeleted", releasedByB, "correct",
                bAcquired && releasedByA == 0 && "B".equals(holder) && releasedByB == 1);
    }

    @ExceptionHandler(IllegalArgumentException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Object invalid(IllegalArgumentException e) {
        return Map.of("error", String.valueOf(e.getMessage()));
    }
}
