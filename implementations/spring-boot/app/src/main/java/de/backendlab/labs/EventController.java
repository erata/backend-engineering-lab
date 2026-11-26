package de.backendlab.labs;
import java.util.*;import java.util.concurrent.*;import org.springframework.context.ApplicationEventPublisher;import org.springframework.context.annotation.*;import org.springframework.jdbc.core.JdbcTemplate;import org.springframework.scheduling.annotation.*;import org.springframework.stereotype.Service;import org.springframework.transaction.annotation.*;import org.springframework.transaction.event.*;import org.springframework.web.bind.annotation.*;

/**
 * Lab 07: a price change with an audit side effect.
 * <ul>
 *   <li>{@code direct} – audit row written in the same transaction (atomic with the price).</li>
 *   <li>{@code event} – AFTER_COMMIT listener running <b>asynchronously</b> on a small bounded executor, in its own
 *       transaction. The request thread commits and returns its connection before the audit needs one.</li>
 *   <li>{@code event-inline} – negative example: AFTER_COMMIT listener with REQUIRES_NEW on the request thread.
 *       The committed outer connection is not yet returned to the pool when the listener asks for a second one, so
 *       under concurrency &gt;= pool size every request waits for a connection that never frees up
 *       (pool-exhaustion deadlock until Hikari's 30 s timeout). Measured in reports/BENCHMARK_REPORT.md.</li>
 * </ul>
 */
@Profile("lab") @RestController @RequestMapping("/lab/events") public class EventController {
 private final PriceService service;public EventController(PriceService service){this.service=service;}
 @PostMapping("/price-change") public Object change(@RequestParam(defaultValue="1") long id,@RequestParam(defaultValue="100") long cents,@RequestParam(defaultValue="event") String mode,@RequestParam(defaultValue="false") boolean rollback){service.change(id,cents,mode,rollback);return Map.of("id",id,"cents",cents,"mode",mode);}
 @ExceptionHandler(IllegalArgumentException.class) @ResponseStatus(org.springframework.http.HttpStatus.BAD_REQUEST) public Object invalid(IllegalArgumentException e){return Map.of("error",String.valueOf(e.getMessage()));}
 public record PriceChanged(long id,long cents){}
 public record InlinePriceChanged(long id,long cents){}

 @Profile("lab") @Configuration @EnableAsync public static class AuditAsyncConfig {
  /**
   * Bounded: 2 threads (well below the 10-connection pool) and a bounded queue. Overflow is rejected (AbortPolicy):
   * CallerRunsPolicy would run the audit on the request thread inside afterCommit and recreate the pool deadlock.
   * A rejected audit is lost and surfaces as an error after the price was committed, which is the audit gap an outbox would close.
   */
  @Bean(name="auditExecutor",destroyMethod="shutdown") ExecutorService auditExecutor(){var n=new java.util.concurrent.atomic.AtomicInteger();return new ThreadPoolExecutor(2,2,0,TimeUnit.SECONDS,new ArrayBlockingQueue<>(10_000),r->{var t=new Thread(r,"audit-"+n.incrementAndGet());t.setDaemon(true);return t;},new ThreadPoolExecutor.AbortPolicy());}
 }

 @Profile("lab") @Service public static class PriceService {private final JdbcTemplate jdbc;private final ApplicationEventPublisher publisher;public PriceService(JdbcTemplate j,ApplicationEventPublisher p){jdbc=j;publisher=p;}
  @Transactional public void change(long id,long cents,String mode,boolean rollback){
   if(id<1||cents<0||!Set.of("direct","event","event-inline").contains(mode))throw new IllegalArgumentException("mode direct|event|event-inline, id>=1, cents>=0");
   jdbc.update("INSERT INTO lab_prices(product_id,cents) VALUES(?,?) ON DUPLICATE KEY UPDATE cents=VALUES(cents)",id,cents);
   switch(mode){case "direct"->audit(id,cents);case "event"->publisher.publishEvent(new PriceChanged(id,cents));default->publisher.publishEvent(new InlinePriceChanged(id,cents));}
   if(rollback)throw new IllegalStateException("intentional rollback");
  }
  @Async("auditExecutor") @TransactionalEventListener(phase=TransactionPhase.AFTER_COMMIT) @Transactional(propagation=Propagation.REQUIRES_NEW) public void after(PriceChanged e){audit(e.id(),e.cents());}
  @TransactionalEventListener(phase=TransactionPhase.AFTER_COMMIT) @Transactional(propagation=Propagation.REQUIRES_NEW) public void afterInline(InlinePriceChanged e){audit(e.id(),e.cents());}
  private void audit(long id,long cents){jdbc.update("INSERT INTO lab_price_audit(product_id,cents) VALUES(?,?)",id,cents);}
 }
}
