package de.backendlab;
import de.backendlab.cache.*;
import com.jayway.jsonpath.JsonPath;
import de.backendlab.catalog.ProductStore;
import de.backendlab.labs.cache.RefreshCoordinator;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.mysql.MySQLContainer;
import javax.sql.DataSource;
import java.net.URI;
import java.net.http.*;
import java.time.Duration;
import java.sql.Connection;
import static org.junit.jupiter.api.Assertions.*;
@Testcontainers
@SpringBootTest(webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT,properties={"spring.profiles.active=lab","lab.refresh-interval=1h","lab.seed-count=100000","lab.sync.strategy=journal","lab.cache.strategy=snapshot"})
class CatalogIT {
    @Container static final MySQLContainer MYSQL=new MySQLContainer("mysql:8.4").withDatabaseName("backendlab").withUsername("lab").withPassword("local-lab-password").withCommand("--log-bin-trust-function-creators=1");
    @DynamicPropertySource static void properties(DynamicPropertyRegistry registry){
        registry.add("spring.datasource.url",()->MYSQL.getJdbcUrl()+(MYSQL.getJdbcUrl().contains("?")?"&":"?")+"connectionTimeZone=UTC&forceConnectionTimeZoneToSession=true&sslMode=DISABLED&allowPublicKeyRetrieval=true&rewriteBatchedStatements=true");
        registry.add("spring.datasource.username",MYSQL::getUsername);registry.add("spring.datasource.password",MYSQL::getPassword);
    }
    @Autowired ProductStore store;
    @Autowired ProductCache cache;
    @Autowired RefreshCoordinator journal;
    @Autowired DataSource dataSource;
    @LocalServerPort int port;
    @Test void catalogAndBothSynchronizationAlgorithms() throws Exception {
        assertTrue(journal.ready());assertEquals(100000,cache.size());assertTrue(store.pending(1).isEmpty());
        var client=HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
        var response=send(client,"GET","/api/products?page=2&size=10",null);
        assertEquals(200,response.statusCode());
        assertEquals(11,((Number)JsonPath.read(response.body(),"$.items[0].id")).intValue());
        assertEquals(10,((java.util.List<?>)JsonPath.read(response.body(),"$.items")).size());
        assertEquals(100000,((Number)JsonPath.read(response.body(),"$.total")).intValue());
        assertEquals(400,send(client,"GET","/api/products?page=0",null).statusCode());
        var created=send(client,"POST","/api/products","{\"name\":\"New via HTTP\"}");assertEquals(201,created.statusCode());
        var location=created.headers().firstValue("Location").orElseThrow();long id=Long.parseLong(location.substring(location.lastIndexOf('/')+1));
        assertTrue(cache.get(id).isEmpty());assertEquals(200,send(client,"POST","/lab/cache/refresh",null).statusCode());
        assertEquals("New via HTTP",cache.get(id).orElseThrow().name());assertNull(cache.get(id).orElseThrow().lastUpdatedTime());
        assertEquals(204,send(client,"PUT","/api/products/"+id,"{\"name\":\"Renamed\"}").statusCode());journal.refresh();
        assertEquals("Renamed",cache.get(id).orElseThrow().name());assertNotNull(cache.get(id).orElseThrow().lastUpdatedTime());
        assertEquals(204,send(client,"DELETE","/api/products/"+id,null).statusCode());journal.refresh();assertTrue(cache.get(id).isEmpty());
        // Do not create a second journal consumer. Baseline is a separate in-memory copy, reads only.
        var baseline=new SnapshotCache();var initial=store.all();baseline.replaceAll(initial);var mark=Watermark.empty().advance(initial);
        long lower=200001, higher=200002;
        try(Connection slow=dataSource.getConnection();Connection fast=dataSource.getConnection()){
            slow.setAutoCommit(false);insert(slow,lower,"Late null insert");insert(fast,higher,"Early null insert");
            var first=store.after(mark);baseline.apply(Changes.upsert(first));mark=mark.advance(first);
            journal.refresh();assertTrue(cache.get(higher).isPresent());assertTrue(cache.get(lower).isEmpty());
            slow.commit();
            var second=store.after(mark);baseline.apply(Changes.upsert(second));
            assertTrue(baseline.get(higher).isPresent());assertTrue(baseline.get(lower).isEmpty(),"ID watermark misses late commit");
            journal.refresh();assertEquals("Late null insert",cache.get(lower).orElseThrow().name());
        }
        try(Connection rolledBack=dataSource.getConnection()){
            rolledBack.setAutoCommit(false);insert(rolledBack,200003,"Rollback");rolledBack.rollback();
        }
        journal.refresh();assertTrue(cache.get(200003).isEmpty());assertTrue(store.pending(1).isEmpty());
    }
    private static void insert(Connection connection,long id,String name)throws Exception{
        try(var statement=connection.prepareStatement("INSERT INTO products(id,name,last_updated_time) VALUES(?,?,NULL)")){
            statement.setLong(1,id);statement.setString(2,name);statement.executeUpdate();
        }
    }
    private HttpResponse<String> send(HttpClient client,String method,String path,String body)throws Exception{
        var req=HttpRequest.newBuilder(URI.create("http://localhost:"+port+path)).timeout(Duration.ofSeconds(20)).header("Content-Type","application/json")
            .method(method,body==null?HttpRequest.BodyPublishers.noBody():HttpRequest.BodyPublishers.ofString(body)).build();
        return client.send(req,HttpResponse.BodyHandlers.ofString());
    }
}
