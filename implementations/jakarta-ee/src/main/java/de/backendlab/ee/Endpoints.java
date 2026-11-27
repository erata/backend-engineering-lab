package de.backendlab.ee;
import jakarta.ws.rs.*;import jakarta.ws.rs.core.MediaType;import jakarta.inject.Inject;import jakarta.annotation.Resource;import jakarta.enterprise.concurrent.ManagedExecutorService;import de.backendlab.experiments.Experiments;import java.net.http.*;import java.util.*;import java.util.concurrent.*;
@Path("/") @Produces(MediaType.APPLICATION_JSON) @jakarta.enterprise.context.ApplicationScoped public class Endpoints {
 @Inject Catalog catalog;@Resource(lookup="java:comp/DefaultManagedExecutorService") ManagedExecutorService executor;private static final HttpClient CLIENT=HttpClient.newHttpClient();
 private void lab(){if(!"true".equals(System.getenv("LAB_ENABLED")))throw new NotFoundException();}
 @GET @Path("api/products") public Object products(@DefaultValue("1") @QueryParam("page") int page,@DefaultValue("10") @QueryParam("size") int size,@DefaultValue("") @QueryParam("search") String search){return catalog.page(page,size,search);}
 @GET @Path("api/products/{id}") public Object product(@PathParam("id") long id){return catalog.get(id);}
 public record NameRequest(String name){}
 private String name(NameRequest req){if(req==null||req.name()==null||req.name().isBlank()||req.name().length()>255)throw new BadRequestException();return req.name().strip();}
 @POST @Path("api/products") @Consumes(MediaType.APPLICATION_JSON) public jakarta.ws.rs.core.Response create(NameRequest req){long id=catalog.create(name(req));return jakarta.ws.rs.core.Response.created(java.net.URI.create("/api/products/"+id)).entity(Map.of("id",id,"cacheVisibility","after refresh")).build();}
 @PUT @Path("api/products/{id}") @Consumes(MediaType.APPLICATION_JSON) public jakarta.ws.rs.core.Response rename(@PathParam("id") long id,NameRequest req){if(!catalog.rename(id,name(req)))throw new NotFoundException();return jakarta.ws.rs.core.Response.noContent().build();}
 @DELETE @Path("api/products/{id}") public jakarta.ws.rs.core.Response delete(@PathParam("id") long id){if(!catalog.delete(id))throw new NotFoundException();return jakarta.ws.rs.core.Response.noContent().build();}
 @GET @Path("api/cache/status") public Object status(){return Map.of("count",catalog.size(),"sync",catalog.sync());}
 @POST @Path("lab/cache/refresh") public Object refresh(){lab();catalog.refresh();return status();}
 @POST @Path("lab/concurrency/reserve") public Object reserve(@DefaultValue("atomic") @QueryParam("mode") String mode,@DefaultValue("1000") @QueryParam("stock") int stock,@DefaultValue("2000") @QueryParam("requests") int requests){lab();return Experiments.reserve(mode,stock,requests,executor);}
 @GET @Path("lab/io/{mode}") public CompletionStage<List<String>> io(@PathParam("mode") String mode){lab();return Experiments.io(CLIENT,System.getenv().getOrDefault("LAB_MOCK_URL","http://localhost:8090"),mode,executor);}
 @GET @Path("lab/threads/info") public Object thread(){lab();return Map.of("runtime",System.getProperty("java.version"),"thread",Thread.currentThread().getName(),"virtual",isVirtual());}

 /**
  * Lab 08: real connection pool (WildFly pools of 5 / 20, declared on {@link Api}); each request holds a connection
  * for SELECT SLEEP(ms). Lives here because JAX-RS gives a class annotated @Path("lab/resources") precedence for every
  * URI under that prefix, which hid stampede/pool when this endpoint had its own resource class (F14).
  */
 @Resource(lookup="java:app/jdbc/Pool5") javax.sql.DataSource pool5;
 @Resource(lookup="java:app/jdbc/Pool20") javax.sql.DataSource pool20;
 @GET @Path("lab/resources/db") public jakarta.ws.rs.core.Response db(@DefaultValue("5") @QueryParam("pool") int pool,@DefaultValue("30") @QueryParam("ms") int ms){
  lab();if((pool!=5&&pool!=20)||ms<1||ms>1000)throw new BadRequestException("pool 5|20, ms 1..1000");
  long t0=System.nanoTime();
  try(var c=(pool==5?pool5:pool20).getConnection()){
   double waitMs=(System.nanoTime()-t0)/1e6;
   try(var st=c.prepareStatement("SELECT SLEEP(?)")){st.setDouble(1,ms/1000.0);st.execute();}
   return jakarta.ws.rs.core.Response.ok(Map.of("pool",pool,"waitMs",waitMs)).build();
  }catch(java.sql.SQLException e){
   return jakarta.ws.rs.core.Response.status(jakarta.ws.rs.core.Response.Status.SERVICE_UNAVAILABLE).entity(Map.of("pool",pool,"error",String.valueOf(e.getMessage()))).build();
  }
 }

 /** Concurrency 3.1 managed executor with virtual=true, declared on {@link Api}. */
 @Resource(lookup="java:app/concurrent/virtual") ManagedExecutorService virtualExecutor;
 private ManagedExecutorService executor(String name){return switch(name){case "virtual"->virtualExecutor;case "default"->executor;default->throw new BadRequestException("executor default|virtual");};}
 private static boolean isVirtual(){try{return (boolean)Thread.class.getMethod("isVirtual").invoke(Thread.currentThread());}catch(ReflectiveOperationException e){return false;}}
 /** Which thread does a task on the chosen managed executor run on? */
 @GET @Path("lab/threads/executor") public CompletionStage<Map<String,Object>> executorInfo(@DefaultValue("virtual") @QueryParam("executor") String name){lab();return executor(name).supplyAsync(()->Map.of("executor",name,"thread",Thread.currentThread().toString(),"virtual",isVirtual()));}
 /**
  * Lab 04 on WildFly: the blocking 3-call chain runs on a managed executor and the JAX-RS request completes
  * asynchronously, so the Undertow worker thread is released while the upstream calls block.
  */
 @GET @Path("lab/io/blocking-async") public CompletionStage<List<String>> blockingAsync(@DefaultValue("virtual") @QueryParam("executor") String name){
  lab();var url=System.getenv().getOrDefault("LAB_MOCK_URL","http://localhost:8090");var chosen=executor(name);
  return chosen.supplyAsync(()->Experiments.io(CLIENT,url,"blocking",chosen).toCompletableFuture().join());
 }
 @GET @Path("lab/cpu/{mode}") public Object cpu(@PathParam("mode") String mode,@DefaultValue("100000") @QueryParam("count") int count,@DefaultValue("100") @QueryParam("rounds") int rounds,@DefaultValue("4") @QueryParam("workers") int workers){lab();return Experiments.cpu(count,rounds,mode.equals("sequential")?1:workers,executor);}
 @GET @Path("lab/resources/stampede") public Object stampede(@DefaultValue("true") @QueryParam("single") boolean single,@DefaultValue("32") @QueryParam("requests") int requests){lab();return Experiments.stampede(requests,single,executor);}
 @GET @Path("lab/resources/pool") public Object pool(@DefaultValue("32") @QueryParam("requests") int requests,@DefaultValue("5") @QueryParam("permits") int permits){lab();return Experiments.pool(requests,permits,executor);}
}
