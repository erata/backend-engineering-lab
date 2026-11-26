package de.backendlab.ee;
import jakarta.enterprise.context.ApplicationScoped;import jakarta.enterprise.event.*;import jakarta.inject.Inject;import jakarta.ws.rs.*;import jakarta.ws.rs.core.MediaType;import java.util.*;import java.util.concurrent.ConcurrentHashMap;import java.util.concurrent.atomic.AtomicLong;
/** An in-memory CDI event demonstration; not a transactional persistence example. */
@Path("lab/events") @Produces(MediaType.APPLICATION_JSON) public class EventResource {
 @Inject PriceBook book;@Inject Event<PriceChanged> events;
 @POST @Path("price-change") public Object change(@DefaultValue("1") @QueryParam("id") long id,@DefaultValue("100") @QueryParam("cents") long cents,@DefaultValue("event") @QueryParam("mode") String mode,@DefaultValue("false") @QueryParam("rollback") boolean rollback){if(!"true".equals(System.getenv("LAB_ENABLED")))throw new NotFoundException();if(id<1||cents<0||(!mode.equals("direct")&&!mode.equals("event")))throw new BadRequestException();if(rollback)throw new BadRequestException("simulated abort before update; no transaction");book.price(id,cents);var e=new PriceChanged(id,cents);if(mode.equals("event"))events.fire(e);else book.audit(e);return Map.of("id",id,"cents",cents,"auditCount",book.auditCount());}
 public record PriceChanged(long id,long cents){}
 @ApplicationScoped public static class PriceBook{final Map<Long,Long> prices=new ConcurrentHashMap<>();final AtomicLong count=new AtomicLong();public void price(long id,long cents){prices.put(id,cents);}public long auditCount(){return count.get();}public void audit(@Observes PriceChanged event){count.incrementAndGet();}}
}
