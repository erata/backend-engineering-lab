package de.backendlab;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;
@SpringBootApplication
@EnableScheduling
public class BackendLabApplication {
    public static void main(String[] args) { SpringApplication.run(BackendLabApplication.class,args); }
}
