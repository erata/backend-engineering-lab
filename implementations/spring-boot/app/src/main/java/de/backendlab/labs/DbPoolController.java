package de.backendlab.labs;
import com.zaxxer.hikari.*;import jakarta.annotation.PreDestroy;import java.sql.*;import java.util.*;import java.util.concurrent.*;import org.springframework.beans.factory.annotation.Value;import org.springframework.context.annotation.Profile;import org.springframework.http.*;import org.springframework.web.bind.annotation.*;

/**
 * Lab 08: a real JDBC connection pool under load. Two dedicated Hikari pools (5 and 20 connections, 1 s acquisition
 * timeout) run {@code SELECT SLEEP(ms)} so that each request holds a connection for a known time.
 * Capacity = pool size / hold time (5 / 30 ms ≈ 166 req/s, 20 / 30 ms ≈ 666 req/s).
 */
@Profile("lab") @RestController @RequestMapping("/lab/resources")
public class DbPoolController {
 private final Map<Integer,HikariDataSource> pools=new ConcurrentHashMap<>();
 private final String url,user,password;
 public DbPoolController(@Value("${spring.datasource.url}") String url,@Value("${spring.datasource.username}") String user,@Value("${spring.datasource.password}") String password){this.url=url;this.user=user;this.password=password;}
 private HikariDataSource pool(int size){
  if(size!=5&&size!=20)throw new IllegalArgumentException("pool 5|20");
  return pools.computeIfAbsent(size,s->{var c=new HikariConfig();c.setJdbcUrl(url);c.setUsername(user);c.setPassword(password);c.setMaximumPoolSize(s);c.setMinimumIdle(s);c.setConnectionTimeout(1000);c.setPoolName("lab-pool-"+s);return new HikariDataSource(c);});
 }
 @GetMapping("/db") public ResponseEntity<Map<String,Object>> db(@RequestParam(defaultValue="5") int pool,@RequestParam(defaultValue="30") int ms) throws SQLException {
  if(ms<1||ms>1000)throw new IllegalArgumentException("ms 1..1000");
  var ds=pool(pool);long t0=System.nanoTime();
  try(Connection c=ds.getConnection()){
   double waitMs=(System.nanoTime()-t0)/1e6;
   try(var st=c.prepareStatement("SELECT SLEEP(?)")){st.setDouble(1,ms/1000.0);st.execute();}
   var mx=ds.getHikariPoolMXBean();
   return ResponseEntity.ok(Map.of("pool",pool,"waitMs",waitMs,"active",mx.getActiveConnections(),"waiting",mx.getThreadsAwaitingConnection()));
  }catch(SQLTransientConnectionException e){
   return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body(Map.of("pool",pool,"error","no connection within 1 s"));
  }
 }
 @ExceptionHandler(IllegalArgumentException.class) @ResponseStatus(HttpStatus.BAD_REQUEST) public Object invalid(IllegalArgumentException e){return Map.of("error",String.valueOf(e.getMessage()));}
 @PreDestroy public void close(){pools.values().forEach(HikariDataSource::close);}
}
