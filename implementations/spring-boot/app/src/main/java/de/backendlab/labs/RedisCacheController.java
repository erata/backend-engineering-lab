package de.backendlab.labs;
import java.time.Duration;import java.util.*;import java.util.concurrent.*;import org.springframework.beans.factory.annotation.Value;import org.springframework.context.annotation.Profile;import org.springframework.data.redis.core.StringRedisTemplate;import org.springframework.jdbc.core.JdbcTemplate;import org.springframework.web.bind.annotation.*;

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
 * Lab simplification: the lock is released with GET + DEL (not an atomic compare-and-delete script) and has a fixed
 * lease; a production lock needs a fencing token or Lua script.
 */
@Profile("lab") @RestController @RequestMapping("/lab/redis")
public class RedisCacheController {
 private static final Duration TTL=Duration.ofSeconds(30),LEASE=Duration.ofSeconds(3);
 private final StringRedisTemplate redis;private final JdbcTemplate jdbc;private final String instance;
 private final ConcurrentHashMap<String,CompletableFuture<String>> inflight=new ConcurrentHashMap<>();
 private static final java.util.concurrent.atomic.AtomicLong FALLBACKS=new java.util.concurrent.atomic.AtomicLong();
 public RedisCacheController(StringRedisTemplate redis,JdbcTemplate jdbc,@Value("${HOSTNAME:local}") String instance){this.redis=redis;this.jdbc=jdbc;this.instance=instance;}

 @GetMapping("/product/{id}") public Map<String,Object> product(@PathVariable long id,@RequestParam(defaultValue="distributed") String mode) throws InterruptedException {
  long t0=System.nanoTime();
  try{return cached(id,mode,t0);}
  catch(org.springframework.dao.DataAccessException e){
   // Fail open: Redis unavailable (connection refused or 500 ms command timeout) -> serve from MySQL without caching.
   // Availability is kept, but every request now hits the database (no stampede protection either).
   FALLBACKS.incrementAndGet();
   String name=jdbc.queryForObject("SELECT name FROM products WHERE id=?",String.class,id);
   return Map.of("value","{\"id\":"+id+",\"name\":\""+name+"\"}","source","db-fallback","instance",instance,"ms",(System.nanoTime()-t0)/1e6,"error",e.getClass().getSimpleName());
  }
 }
 private Map<String,Object> cached(long id,String mode,long t0) throws InterruptedException {
  String key="lab:product:"+id;
  String value=redis.opsForValue().get(key);String source="redis";
  if(value==null){
   source="loaded-or-waited";
   value=switch(mode){case "none"->load(id,key);case "local"->local(id,key);case "distributed"->distributed(id,key);default->throw new IllegalArgumentException("mode none|local|distributed");};
  }
  return Map.of("value",value,"source",source,"instance",instance,"ms",(System.nanoTime()-t0)/1e6);
 }
 private String load(long id,String key){
  redis.opsForValue().increment("lab:loads:"+id);
  String name=jdbc.queryForObject("SELECT name FROM products WHERE id=?",String.class,id);
  try{Thread.sleep(100);}catch(InterruptedException e){Thread.currentThread().interrupt();throw new IllegalStateException(e);}
  String json="{\"id\":"+id+",\"name\":\""+name.replace("\\","\\\\").replace("\"","\\\"")+"\"}";
  redis.opsForValue().set(key,json,TTL);return json;
 }
 private String local(long id,String key){
  var mine=new CompletableFuture<String>();var leader=inflight.putIfAbsent(key,mine);
  if(leader!=null)return leader.join();
  try{String v=redis.opsForValue().get(key);if(v==null)v=load(id,key);mine.complete(v);return v;}
  catch(RuntimeException e){mine.completeExceptionally(e);throw e;}
  finally{inflight.remove(key,mine);}
 }
 private String distributed(long id,String key) throws InterruptedException {
  String lock="lab:lock:"+id;long deadline=System.nanoTime()+LEASE.toNanos();
  while(System.nanoTime()<deadline){
   String token=instance+"-"+UUID.randomUUID();
   if(Boolean.TRUE.equals(redis.opsForValue().setIfAbsent(lock,token,LEASE))){
    try{String v=redis.opsForValue().get(key);return v!=null?v:load(id,key);}
    finally{if(Objects.equals(token,redis.opsForValue().get(lock)))redis.delete(lock);}
   }
   Thread.sleep(10);String v=redis.opsForValue().get(key);if(v!=null)return v;
  }
  throw new IllegalStateException("lock not acquired within lease");
 }
 /** Explicit invalidation after a write; without it other instances serve the old value until the 30 s TTL expires. */
 @PostMapping("/invalidate") public Map<String,Object> invalidate(@RequestParam(defaultValue="42") long id){return Map.of("invalidated",Boolean.TRUE.equals(redis.delete("lab:product:"+id)));}
 @PostMapping("/reset") public Map<String,Object> reset(@RequestParam(defaultValue="42") long id){redis.delete(List.of("lab:product:"+id,"lab:loads:"+id,"lab:lock:"+id));return Map.of("reset",id);}
 @GetMapping("/loads") public Map<String,Object> loads(@RequestParam(defaultValue="42") long id){String v=redis.opsForValue().get("lab:loads:"+id);return Map.of("id",id,"loads",v==null?0:Long.parseLong(v),"fallbacks",FALLBACKS.get(),"client","Lettuce");}
 @ExceptionHandler(IllegalArgumentException.class) @ResponseStatus(org.springframework.http.HttpStatus.BAD_REQUEST) public Object invalid(IllegalArgumentException e){return Map.of("error",String.valueOf(e.getMessage()));}
}
