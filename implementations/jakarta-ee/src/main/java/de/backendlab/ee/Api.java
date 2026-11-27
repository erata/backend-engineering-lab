package de.backendlab.ee;
import jakarta.annotation.sql.DataSourceDefinition;import jakarta.enterprise.concurrent.ManagedExecutorDefinition;import jakarta.ws.rs.ApplicationPath;import jakarta.ws.rs.core.Application;

/**
 * JAX-RS application plus container-managed resources declared in code (no server CLI configuration needed):
 * <ul>
 *   <li>{@code java:app/jdbc/LabDS} – JTA datasource for the transactional domain-event lab (Lab 07).</li>
 *   <li>{@code java:app/jdbc/Pool5}, {@code java:app/jdbc/Pool20} – pools of 5 / 20 connections for the real
 *       connection-pool lab (Lab 08).</li>
 *   <li>{@code java:app/concurrent/virtual} – Jakarta Concurrency 3.1 managed executor backed by virtual threads (Lab 04).</li>
 * </ul>
 * The JDBC URL and credentials are the Docker Compose defaults of the {@code jakarta-db} service; annotation values
 * must be constants.
 */
@DataSourceDefinition(name="java:app/jdbc/LabDS",className="com.mysql.cj.jdbc.MysqlDataSource",url=Api.URL,user="lab",password="local-lab-password",minPoolSize=0,maxPoolSize=20,transactional=true)
@DataSourceDefinition(name="java:app/jdbc/Pool5",className="com.mysql.cj.jdbc.MysqlDataSource",url=Api.URL,user="lab",password="local-lab-password",minPoolSize=5,maxPoolSize=5,transactional=false)
@DataSourceDefinition(name="java:app/jdbc/Pool20",className="com.mysql.cj.jdbc.MysqlDataSource",url=Api.URL,user="lab",password="local-lab-password",minPoolSize=20,maxPoolSize=20,transactional=false)
@ManagedExecutorDefinition(name="java:app/concurrent/virtual",virtual=true)
@ApplicationPath("/") public class Api extends Application {
 static final String URL="jdbc:mysql://jakarta-db:3306/backendlab?sslMode=DISABLED&allowPublicKeyRetrieval=true&connectionTimeZone=UTC";
}
