package de.backendlab.labs;
import java.util.*;import java.util.concurrent.atomic.AtomicLong;import org.springframework.context.annotation.*;import org.springframework.stereotype.Component;import org.springframework.web.context.annotation.RequestScope;import org.springframework.web.bind.annotation.*;import de.backendlab.cache.ProductGenerator;
@Profile("lab") @RestController @RequestMapping("/lab/di")
public class DiController {
 @Profile("lab") @Component @RequestScope public static class PerRequest {private final List<?> data=ProductGenerator.generate(100000);private final long id=IDS.incrementAndGet();public long id(){return id;}public int size(){return data.size();}}
 @Profile("lab") @Component public static class Shared {private final List<?> data=ProductGenerator.generate(100000);private final long id=IDS.incrementAndGet();public long id(){return id;}public int size(){return data.size();}}
 private static final AtomicLong IDS=new AtomicLong();private final PerRequest request;private final Shared shared;public DiController(PerRequest request,Shared shared){this.request=request;this.shared=shared;}
 @GetMapping("/instances") public Object instances(@RequestParam(defaultValue="shared") String mode){return mode.equals("request")?Map.of("id",request.id(),"count",request.size()):Map.of("id",shared.id(),"count",shared.size());}
}
