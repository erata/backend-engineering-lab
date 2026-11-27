package de.backendlab.labs;
import java.util.*;import java.util.concurrent.atomic.AtomicLong;import org.springframework.beans.factory.ObjectProvider;import org.springframework.beans.factory.annotation.Autowired;import org.springframework.context.annotation.*;import org.springframework.stereotype.Component;import org.springframework.web.context.annotation.RequestScope;import org.springframework.web.bind.annotation.*;import de.backendlab.cache.ProductGenerator;

/**
 * Lab 06: DI lifetimes.
 * <ul>
 *   <li>{@code /instances} – heavy payload per request ({@code @RequestScope}) vs shared singleton.</li>
 *   <li>{@code /captive} – a prototype bean injected into a singleton is created once and then lives as long as the
 *       singleton (captive dependency); {@code ObjectProvider.getObject()} creates a new one on every call.</li>
 *   <li>{@code /mutable} – per-request user stored in a singleton field (shared mutable state, races under concurrency)
 *       vs in a request-scoped bean.</li>
 * </ul>
 */
@Profile("lab") @RestController @RequestMapping("/lab/di")
public class DiController {
 @Profile("lab") @Component @RequestScope public static class PerRequest {private final List<?> data=ProductGenerator.generate(100000);private final long id=IDS.incrementAndGet();public long id(){return id;}public int size(){return data.size();}}
 @Profile("lab") @Component public static class Shared {private final List<?> data=ProductGenerator.generate(100000);private final long id=IDS.incrementAndGet();public long id(){return id;}public int size(){return data.size();}}

 /** Cheap prototype: a new instance every time the container is asked for one. */
 @Profile("lab") @Component @Scope("prototype") public static class Prototype {private final long id=IDS.incrementAndGet();public long id(){return id;}}
 /** Singleton holding a prototype captured at construction time, plus a provider for the correct variant. */
 @Profile("lab") @Component public static class CaptiveHolder {
  private final Prototype captured;private final ObjectProvider<Prototype> provider;
  public CaptiveHolder(Prototype captured,ObjectProvider<Prototype> provider){this.captured=captured;this.provider=provider;}
  long captured(){return captured.id();} long fresh(){return provider.getObject().id();}
 }

 /**
  * Resource ownership: Spring creates prototype beans but does <b>not</b> manage their destruction — @PreDestroy is
  * never called for prototypes. Whoever asks the container for a prototype owns it and must close it.
  */
 @Profile("lab") @Component @Scope("prototype") public static class OwnedResource implements AutoCloseable {
  static final AtomicLong CREATED=new AtomicLong(),CLOSED=new AtomicLong();
  public OwnedResource(){CREATED.incrementAndGet();}
  @jakarta.annotation.PreDestroy @Override public void close(){CLOSED.incrementAndGet();}
 }

 /** Holds "the current user" – fine per request, a data leak when shared. */
 public interface UserHolder {void set(String user);String get();}
 @Profile("lab") @Component("singletonUserHolder") public static class SingletonUserHolder implements UserHolder {private String user;public void set(String u){user=u;}public String get(){return user;}}
 @Profile("lab") @Component("requestUserHolder") @RequestScope public static class RequestUserHolder implements UserHolder {private String user;public void set(String u){user=u;}public String get(){return user;}}

 private static final AtomicLong IDS=new AtomicLong();
 private final PerRequest request;private final Shared shared;private final CaptiveHolder captive;private final UserHolder singletonUser;private final UserHolder requestUser;
 public DiController(PerRequest request,Shared shared,CaptiveHolder captive,@org.springframework.beans.factory.annotation.Qualifier("singletonUserHolder") UserHolder singletonUser,@org.springframework.beans.factory.annotation.Qualifier("requestUserHolder") UserHolder requestUser){this.request=request;this.shared=shared;this.captive=captive;this.singletonUser=singletonUser;this.requestUser=requestUser;}

 @GetMapping("/instances") public Object instances(@RequestParam(defaultValue="shared") String mode){return mode.equals("request")?Map.of("id",request.id(),"count",request.size()):Map.of("id",shared.id(),"count",shared.size());}

 @GetMapping("/captive") public Object captive(@RequestParam(defaultValue="captured") String mode){
  return switch(mode){case "captured"->Map.of("mode",mode,"id",captive.captured());case "provider"->Map.of("mode",mode,"id",captive.fresh());default->throw new IllegalArgumentException("mode captured|provider");};
 }

 /** mode=container: rely on the container to clean up (it will not); mode=caller: the caller closes what it obtained. */
 @GetMapping("/ownership") public Object ownership(@RequestParam(defaultValue="container") String mode,@RequestParam(defaultValue="100") int n){
  if(n<1||n>10000)throw new IllegalArgumentException("n 1..10000");
  long c0=OwnedResource.CREATED.get(),d0=OwnedResource.CLOSED.get();
  for(int i=0;i<n;i++){
   switch(mode){case "container"->ownedProvider.getObject();case "caller"->{try(var r=ownedProvider.getObject()){/* use */}}default->throw new IllegalArgumentException("mode container|caller");}
  }
  return Map.of("mode",mode,"created",OwnedResource.CREATED.get()-c0,"closed",OwnedResource.CLOSED.get()-d0);
 }
 @Autowired private ObjectProvider<OwnedResource> ownedProvider;

 @GetMapping("/mutable") public Object mutable(@RequestParam(defaultValue="singleton") String mode,@RequestParam String user,@RequestParam(defaultValue="5") int delayMs) throws InterruptedException {
  if(delayMs<0||delayMs>100)throw new IllegalArgumentException("delayMs 0..100");
  UserHolder holder=switch(mode){case "singleton"->singletonUser;case "request"->requestUser;default->throw new IllegalArgumentException("mode singleton|request");};
  holder.set(user);Thread.sleep(delayMs);String seen=holder.get();   // simulates work between "authenticate" and "authorize/respond"
  return Map.of("mode",mode,"expected",user,"actual",seen,"correct",user.equals(seen));
 }
 @ExceptionHandler(IllegalArgumentException.class) @ResponseStatus(org.springframework.http.HttpStatus.BAD_REQUEST) public Object invalid(IllegalArgumentException e){return Map.of("error",String.valueOf(e.getMessage()));}
}
