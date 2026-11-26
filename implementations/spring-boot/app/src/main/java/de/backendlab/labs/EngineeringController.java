package de.backendlab.labs;
import de.backendlab.experiments.Experiments;import java.util.*;import java.util.concurrent.*;import java.net.http.*;import org.springframework.context.annotation.Profile;import org.springframework.web.bind.annotation.*;import org.springframework.beans.factory.annotation.Value;import jakarta.annotation.PreDestroy;
@Profile("lab") @RestController @RequestMapping("/lab")
public class EngineeringController {
 private final ExecutorService executor=Executors.newFixedThreadPool(32);private final HttpClient client=HttpClient.newHttpClient();
 @Value("${LAB_MOCK_URL:http://localhost:8090}") String mock;
 @PreDestroy public void stop(){executor.shutdownNow();}
 @PostMapping("/concurrency/reserve") public Object reserve(@RequestParam(defaultValue="atomic") String mode,@RequestParam(defaultValue="1000") int stock,@RequestParam(defaultValue="2000") int requests){return Experiments.reserve(mode,stock,requests,executor);}
 @GetMapping("/io/{mode}") public CompletionStage<List<String>> io(@PathVariable String mode){return Experiments.io(client,mock,mode,executor);}
 @GetMapping("/io/concurrent-blocking") public CompletionStage<List<String>> concurrentBlocking(@RequestParam(defaultValue="platform") String threadModel){
  ExecutorService selected=executor;if(threadModel.equals("virtual")){try{selected=(ExecutorService)Executors.class.getMethod("newVirtualThreadPerTaskExecutor").invoke(null);}catch(ReflectiveOperationException e){throw new IllegalArgumentException("Virtual threads require Java 21+");}}else if(!threadModel.equals("platform"))throw new IllegalArgumentException("thread model");
  final ExecutorService chosen=selected;var jobs=List.of("product","inventory","pricing").stream().map(path->CompletableFuture.supplyAsync(()->{try{var resp=client.send(java.net.http.HttpRequest.newBuilder(java.net.URI.create(mock+"/"+path)).timeout(java.time.Duration.ofSeconds(5)).build(),java.net.http.HttpResponse.BodyHandlers.ofString());if(resp.statusCode()!=200)throw new IllegalStateException("upstream failure");return resp.body();}catch(InterruptedException e){Thread.currentThread().interrupt();throw new CompletionException(e);}catch(java.io.IOException e){throw new CompletionException(e);}},chosen)).toList();return CompletableFuture.allOf(jobs.toArray(CompletableFuture[]::new)).thenApply(v->jobs.stream().map(CompletableFuture::join).toList()).whenComplete((v,e)->{if(chosen!=executor)chosen.shutdown();});
 }
 @GetMapping("/threads/info") public Object threads(){return Map.of("runtime",System.getProperty("java.version"),"thread",Thread.currentThread().getName(),"virtual",virtual());}
 private boolean virtual(){try{return (boolean)Thread.class.getMethod("isVirtual").invoke(Thread.currentThread());}catch(ReflectiveOperationException e){return false;}}
 @GetMapping("/cpu/{mode}") public Object cpu(@PathVariable String mode,@RequestParam(defaultValue="100000") int count,@RequestParam(defaultValue="100") int rounds,@RequestParam(defaultValue="4") int workers){return Experiments.cpu(count,rounds,mode.equals("sequential")?1:workers,executor);}
 @GetMapping("/resources/stampede") public Object stampede(@RequestParam(defaultValue="true") boolean single,@RequestParam(defaultValue="32") int requests){return Experiments.stampede(requests,single,executor);}
 @GetMapping("/resources/pool") public Object pool(@RequestParam(defaultValue="32") int requests,@RequestParam(defaultValue="5") int permits){return Experiments.pool(requests,permits,executor);}
 @ExceptionHandler(IllegalArgumentException.class) @ResponseStatus(org.springframework.http.HttpStatus.BAD_REQUEST) public Object invalid(IllegalArgumentException e){return Map.of("error",e.getMessage());}
}
