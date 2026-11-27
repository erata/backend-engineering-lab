package de.backendlab.ee;
import jakarta.enterprise.context.*;import jakarta.enterprise.inject.Instance;import jakarta.inject.Inject;import jakarta.ws.rs.*;import jakarta.ws.rs.core.MediaType;import de.backendlab.cache.ProductGenerator;import java.util.*;import java.util.concurrent.atomic.AtomicLong;

/**
 * Lab 06 (CDI): heavy payload per request vs application scope; captive {@code @Dependent} bean inside an
 * {@code @ApplicationScoped} bean vs {@code Instance<T>.get()}; current user in an application-scoped field vs a
 * request-scoped bean.
 */
@Path("lab/di") @Produces(MediaType.APPLICATION_JSON) @RequestScoped public class DiResource {
 @Inject RequestData request; @Inject SharedData shared; @Inject CaptiveHolder captive; @Inject SingletonUserHolder singletonUser; @Inject RequestUserHolder requestUser; @Inject OwnerHolder owner; @Inject BackgroundWork background;
 private static void lab(){if(!"true".equals(System.getenv("LAB_ENABLED")))throw new NotFoundException();}

 @GET @Path("instances") public Object instances(@DefaultValue("shared") @QueryParam("mode") String mode){lab();return mode.equals("request")?Map.of("id",request.id(),"count",request.size()):Map.of("id",shared.id(),"count",shared.size());}

 @GET @Path("captive") public Object captive(@DefaultValue("captured") @QueryParam("mode") String mode){
  lab();return switch(mode){case "captured"->Map.of("mode",mode,"id",captive.captured());case "provider"->Map.of("mode",mode,"id",captive.fresh());default->throw new BadRequestException("mode captured|provider");};
 }

 @GET @Path("mutable") public Object mutable(@DefaultValue("singleton") @QueryParam("mode") String mode,@QueryParam("user") String user,@DefaultValue("5") @QueryParam("delayMs") int delayMs) throws InterruptedException {
  lab();if(user==null||delayMs<0||delayMs>100)throw new BadRequestException("user required, delayMs 0..100");
  UserHolder holder=switch(mode){case "singleton"->singletonUser;case "request"->requestUser;default->throw new BadRequestException("mode singleton|request");};
  holder.set(user);Thread.sleep(delayMs);String seen=holder.get();
  return Map.of("mode",mode,"expected",user,"actual",seen,"correct",user.equals(seen));
 }

 /** mode=leak: Instance.get() without destroy(); mode=destroy: the caller destroys what it obtained. */
 @GET @Path("ownership") public Object ownership(@DefaultValue("leak") @QueryParam("mode") String mode,@DefaultValue("100") @QueryParam("n") int n){
  lab();if(n<1||n>10000)throw new BadRequestException("n 1..10000");
  long c0=OwnedResource.CREATED.get(),d0=OwnedResource.CLOSED.get();
  switch(mode){case "leak"->owner.leak(n);case "destroy"->owner.destroy(n);default->throw new BadRequestException("mode leak|destroy");}
  return Map.of("mode",mode,"created",OwnedResource.CREATED.get()-c0,"destroyed",OwnedResource.CLOSED.get()-d0);
 }
 /** A background task (managed executor thread) touching a @RequestScoped bean, without and with @ActivateRequestContext. */
 @GET @Path("background") public Object backgroundTask(@DefaultValue("plain") @QueryParam("mode") String mode){
  lab();return switch(mode){case "plain"->Map.of("mode",mode,"result",background.plain());case "activated"->Map.of("mode",mode,"result",background.activated());default->throw new BadRequestException("mode plain|activated");};
 }

 private static final AtomicLong IDS=new AtomicLong();
 @Dependent public static class OwnedResource {static final AtomicLong CREATED=new AtomicLong(),CLOSED=new AtomicLong();@jakarta.annotation.PostConstruct void open(){CREATED.incrementAndGet();}@jakarta.annotation.PreDestroy void close(){CLOSED.incrementAndGet();}}
 /** Dependent objects obtained via Instance.get() belong to the Instance owner until destroy() - in an application-scoped bean that means forever. */
 @ApplicationScoped public static class OwnerHolder {
  @Inject Instance<OwnedResource> resources;
  public void leak(int n){for(int i=0;i<n;i++)resources.get();}
  public void destroy(int n){for(int i=0;i<n;i++){var r=resources.get();resources.destroy(r);}}
 }
 @ApplicationScoped public static class BackgroundWork {
  @jakarta.annotation.Resource(lookup="java:comp/DefaultManagedExecutorService") jakarta.enterprise.concurrent.ManagedExecutorService executor;
  @Inject RequestUserHolder user; @Inject ContextualTask task;
  public String plain(){return executor.supplyAsync(()->{try{user.set("worker");return "ok: "+user.get();}catch(RuntimeException e){return e.getClass().getSimpleName();}}).join();}
  public String activated(){return executor.supplyAsync(()->task.run()).join();}
 }
 /** @ActivateRequestContext starts a fresh request context for the duration of the method (and destroys it afterwards). */
 @ApplicationScoped public static class ContextualTask {
  @Inject RequestUserHolder user;
  @jakarta.enterprise.context.control.ActivateRequestContext public String run(){user.set("worker");return "ok: "+user.get();}
 }
 @RequestScoped public static class RequestData {private final List<?> data=ProductGenerator.generate(100000);private final String id=UUID.randomUUID().toString();public String id(){return id;}public int size(){return data.size();}}
 @ApplicationScoped public static class SharedData {private final List<?> data=ProductGenerator.generate(100000);private final String id=UUID.randomUUID().toString();public String id(){return id;}public int size(){return data.size();}}

 /** {@code @Dependent} = new instance per injection point; its lifetime is that of the bean it is injected into. */
 @Dependent public static class DependentThing {private final long id=IDS.incrementAndGet();public long id(){return id;}}
 @ApplicationScoped public static class CaptiveHolder {
  @Inject DependentThing captured; @Inject Instance<DependentThing> provider;
  public long captured(){return captured.id();}
  public long fresh(){var thing=provider.get();try{return thing.id();}finally{provider.destroy(thing);}}
 }

 public interface UserHolder {void set(String user);String get();}
 @ApplicationScoped public static class SingletonUserHolder implements UserHolder {private String user;public void set(String u){user=u;}public String get(){return user;}}
 @RequestScoped public static class RequestUserHolder implements UserHolder {private String user;public void set(String u){user=u;}public String get(){return user;}}
}
