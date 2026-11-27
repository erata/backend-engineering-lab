package de.backendlab.ee;
import jakarta.annotation.Resource;import jakarta.enterprise.context.ApplicationScoped;import jakarta.ws.rs.*;import jakarta.ws.rs.core.*;import java.sql.*;import java.util.Map;import javax.sql.DataSource;

/** Lab 08: real connection pool (WildFly IronJacamar pools of 5 / 20) holding each connection for {@code SELECT SLEEP(ms)}. */
@Path("lab/resources") @Produces(MediaType.APPLICATION_JSON) @ApplicationScoped public class DbPoolResource {
 @Resource(lookup="java:app/jdbc/Pool5") DataSource pool5;
 @Resource(lookup="java:app/jdbc/Pool20") DataSource pool20;
 @GET @Path("db") public Response db(@DefaultValue("5") @QueryParam("pool") int pool,@DefaultValue("30") @QueryParam("ms") int ms){
  if(!"true".equals(System.getenv("LAB_ENABLED")))throw new NotFoundException();
  if((pool!=5&&pool!=20)||ms<1||ms>1000)throw new BadRequestException("pool 5|20, ms 1..1000");
  long t0=System.nanoTime();
  try(Connection c=(pool==5?pool5:pool20).getConnection()){
   double waitMs=(System.nanoTime()-t0)/1e6;
   try(var st=c.prepareStatement("SELECT SLEEP(?)")){st.setDouble(1,ms/1000.0);st.execute();}
   return Response.ok(Map.of("pool",pool,"waitMs",waitMs)).build();
  }catch(SQLException e){
   return Response.status(Response.Status.SERVICE_UNAVAILABLE).entity(Map.of("pool",pool,"error",String.valueOf(e.getMessage()))).build();
  }
 }
}
