package de.backendlab.ee;
import jakarta.enterprise.context.*;import jakarta.inject.Inject;import jakarta.ws.rs.*;import jakarta.ws.rs.core.MediaType;import de.backendlab.cache.ProductGenerator;import java.util.*;
@Path("lab/di") @Produces(MediaType.APPLICATION_JSON) public class DiResource {
 @Inject RequestData request; @Inject SharedData shared;
 @GET @Path("instances") public Object instances(@DefaultValue("shared") @QueryParam("mode") String mode){if(!"true".equals(System.getenv("LAB_ENABLED")))throw new NotFoundException();return mode.equals("request")?Map.of("id",request.id(),"count",request.size()):Map.of("id",shared.id(),"count",shared.size());}
 @RequestScoped public static class RequestData {private final List<?> data=ProductGenerator.generate(100000);private final String id=UUID.randomUUID().toString();public String id(){return id;}public int size(){return data.size();}}
 @ApplicationScoped public static class SharedData {private final List<?> data=ProductGenerator.generate(100000);private final String id=UUID.randomUUID().toString();public String id(){return id;}public int size(){return data.size();}}
}
