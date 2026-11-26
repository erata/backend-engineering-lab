package de.backendlab.catalog;
import de.backendlab.cache.*;
import de.backendlab.labs.cache.RefreshCoordinator;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;
import java.net.URI;
import java.util.Map;
@RestController
@RequestMapping("/api/products")
public class ProductController {
    private final ProductCache cache; private final ProductStore store; private final RefreshCoordinator refresh;
    public ProductController(ProductCache cache,ProductStore store,RefreshCoordinator refresh){this.cache=cache;this.store=store;this.refresh=refresh;}
    @GetMapping public ProductPage page(@RequestParam(name="page", defaultValue="1") int page,@RequestParam(name="size", defaultValue="10") int size,@RequestParam(name="search", defaultValue="") String search){
        ready(); if(page<1||size<1||size>100||search.length()>255)throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"invalid pagination or search");
        return cache.page(page,size,search);
    }
    @GetMapping("/{id}") public Product get(@PathVariable("id") long id){ready();return cache.get(id).orElseThrow(()->new ResponseStatusException(HttpStatus.NOT_FOUND,"not in current cache"));}
    public record NameRequest(String name) {}
    @PostMapping public ResponseEntity<Map<String,Object>> create(@RequestBody NameRequest input){
        ready();long id=store.create(name(input));return ResponseEntity.created(URI.create("/api/products/"+id)).body(Map.of("id",id,"cacheVisibility","after refresh"));
    }
    @PutMapping("/{id}") public ResponseEntity<Void> rename(@PathVariable("id") long id,@RequestBody NameRequest input){
        ready();if(!store.rename(id,name(input)))throw new ResponseStatusException(HttpStatus.NOT_FOUND);return ResponseEntity.noContent().build();
    }
    @DeleteMapping("/{id}") public ResponseEntity<Void> delete(@PathVariable("id") long id){
        ready();if(!store.delete(id))throw new ResponseStatusException(HttpStatus.NOT_FOUND);return ResponseEntity.noContent().build();
    }
    private String name(NameRequest input){if(input==null||input.name()==null||input.name().isBlank()||input.name().length()>255)throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"name must contain 1..255 characters");return input.name().strip();}
    private void ready(){if(!refresh.ready())throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,"cache warming up");}
}
