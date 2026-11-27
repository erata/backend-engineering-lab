ARG JAVA_VERSION=25
FROM maven:3.9-eclipse-temurin-26 AS build
WORKDIR /src
COPY implementations/ ./implementations/
WORKDIR /src/implementations/spring-boot
RUN mvn -B -pl app -am package -DskipTests
FROM eclipse-temurin:${JAVA_VERSION}-jre
WORKDIR /app
COPY --from=build /src/implementations/spring-boot/app/target/app-0.1.0.jar /app/app.jar
USER 10001:10001
EXPOSE 8080
ENTRYPOINT ["java","-jar","/app/app.jar"]
