FROM maven:3.9.11-eclipse-temurin-25 AS build
WORKDIR /src
COPY implementations/ implementations/
RUN mvn -B -f implementations/spring-boot/pom.xml -pl ../jakarta-ee -am package -DskipTests
FROM quay.io/wildfly/wildfly:42.0.0.Final-jdk25
COPY --from=build /src/implementations/jakarta-ee/target/ROOT.war /opt/jboss/wildfly/standalone/deployments/ROOT.war
