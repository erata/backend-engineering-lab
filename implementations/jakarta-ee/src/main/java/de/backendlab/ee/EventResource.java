package de.backendlab.ee;
import jakarta.annotation.Resource;import jakarta.enterprise.concurrent.ManagedExecutorService;import jakarta.enterprise.context.ApplicationScoped;import jakarta.enterprise.event.*;import jakarta.inject.Inject;import jakarta.transaction.Transactional;import jakarta.ws.rs.*;import jakarta.ws.rs.core.MediaType;import java.sql.*;import java.util.*;import javax.sql.DataSource;

/**
 * Lab 07 (Jakarta EE): price change + audit with a real JTA transaction on MySQL.
 * <ul>
 *   <li>{@code direct} – audit insert inside the same JTA transaction.</li>
 *   <li>{@code event} – CDI event observed {@code during = AFTER_SUCCESS}; the observer hands the audit to the managed
 *       executor, where it runs in its own transaction ({@code REQUIRES_NEW}).</li>
 *   <li>{@code event-inline} – the AFTER_SUCCESS observer writes the audit synchronously in {@code REQUIRES_NEW} on
 *       the request thread (the pattern that deadlocks Spring's Hikari pool; compare the behaviour here).</li>
 *   <li>{@code rollback=true} – runtime exception after the update: JTA rolls back, AFTER_SUCCESS observers do not run.</li>
 * </ul>
 */
@Path("lab/events") @Produces(MediaType.APPLICATION_JSON) public class EventResource {
 @Inject PriceService service;
 private static void lab(){if(!"true".equals(System.getenv("LAB_ENABLED")))throw new NotFoundException();}
 @POST @Path("price-change") public Object change(@DefaultValue("1") @QueryParam("id") long id,@DefaultValue("100") @QueryParam("cents") long cents,@DefaultValue("event") @QueryParam("mode") String mode,@DefaultValue("false") @QueryParam("rollback") boolean rollback,@DefaultValue("false") @QueryParam("failAudit") boolean failAudit){
  lab();if(id<1||cents<0||!Set.of("direct","event","event-inline").contains(mode))throw new BadRequestException("mode direct|event|event-inline");
  service.change(id,cents,mode,rollback,failAudit);return Map.of("id",id,"cents",cents,"mode",mode);
 }
 @GET @Path("state") public Object state(@DefaultValue("1") @QueryParam("id") long id){lab();return service.state(id);}

 public record PriceChanged(long id,long cents,boolean fail){}
 public record InlinePriceChanged(long id,long cents,boolean fail){}

 @ApplicationScoped public static class PriceService {
  @Resource(lookup="java:app/jdbc/LabDS") DataSource ds;
  @Resource(lookup="java:comp/DefaultManagedExecutorService") ManagedExecutorService executor;
  @Inject Event<PriceChanged> events; @Inject Event<InlinePriceChanged> inline; @Inject Auditor auditor;
  @Transactional public void change(long id,long cents,String mode,boolean rollback,boolean failAudit){
   try(Connection c=ds.getConnection()){
    try(var p=c.prepareStatement("INSERT INTO lab_prices(product_id,cents) VALUES(?,?) ON DUPLICATE KEY UPDATE cents=VALUES(cents)")){p.setLong(1,id);p.setLong(2,cents);p.executeUpdate();}
    switch(mode){case "direct"->Auditor.insert(c,id,cents,failAudit);case "event"->events.fire(new PriceChanged(id,cents,failAudit));default->inline.fire(new InlinePriceChanged(id,cents,failAudit));}
   }catch(SQLException e){throw new IllegalStateException(e);}
   if(rollback)throw new IllegalStateException("intentional rollback");
  }
  void afterSuccess(@Observes(during=TransactionPhase.AFTER_SUCCESS) PriceChanged e){executor.execute(()->auditor.audit(e.id(),e.cents(),e.fail()));}
  void afterSuccessInline(@Observes(during=TransactionPhase.AFTER_SUCCESS) InlinePriceChanged e){auditor.audit(e.id(),e.cents(),e.fail());}
  public Map<String,Object> state(long id){
   try(Connection c=ds.getConnection();var a=c.prepareStatement("SELECT COUNT(*) FROM lab_price_audit WHERE product_id=?");var p=c.prepareStatement("SELECT cents FROM lab_prices WHERE product_id=?")){
    a.setLong(1,id);p.setLong(1,id);long audits;try(var rs=a.executeQuery()){rs.next();audits=rs.getLong(1);}
    long cents=-1;try(var rs=p.executeQuery()){if(rs.next())cents=rs.getLong(1);}
    return Map.of("id",id,"auditCount",audits,"cents",cents);
   }catch(SQLException e){throw new IllegalStateException(e);}
  }
 }

 @ApplicationScoped public static class Auditor {
  @Resource(lookup="java:app/jdbc/LabDS") DataSource ds;
  @Transactional(Transactional.TxType.REQUIRES_NEW) public void audit(long id,long cents,boolean fail){try(Connection c=ds.getConnection()){insert(c,id,cents,fail);}catch(SQLException e){throw new IllegalStateException(e);}}
  /** fail simulates a failing side effect (Lab 07 handler-failure probe). */
  static void insert(Connection c,long id,long cents,boolean fail)throws SQLException{if(fail)throw new IllegalStateException("simulated audit failure");try(var p=c.prepareStatement("INSERT INTO lab_price_audit(product_id,cents) VALUES(?,?)")){p.setLong(1,id);p.setLong(2,cents);p.executeUpdate();}}
 }
}
