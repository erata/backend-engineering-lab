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
 @GET @Path("lab/threads/info") public Object thread(){lab();return Map.of("runtime",System.getProperty("java.version"),"thread",Thread.currentThread().getName());}
 @GET @Path("lab/cpu/{mode}") public Object cpu(@PathParam("mode") String mode,@DefaultValue("100000") @QueryParam("count") int count,@DefaultValue("100") @QueryParam("rounds") int rounds,@DefaultValue("4") @QueryParam("workers") int workers){lab();return Experiments.cpu(count,rounds,mode.equals("sequential")?1:workers,executor);}
 @GET @Path("lab/resources/stampede") public Object stampede(@DefaultValue("true") @QueryParam("single") boolean single,@DefaultValue("32") @QueryParam("requests") int requests){lab();return Experiments.stampede(requests,single,executor);}
 @GET @Path("lab/resources/pool") public Object pool(@DefaultValue("32") @QueryParam("requests") int requests,@DefaultValue("5") @QueryParam("permits") int permits){lab();return Experiments.pool(requests,permits,executor);}
}
