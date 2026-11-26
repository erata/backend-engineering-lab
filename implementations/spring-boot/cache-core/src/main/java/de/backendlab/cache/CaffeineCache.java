package de.backendlab.cache;
import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import java.util.*;
/** No eviction or TTL: full-catalog semantics must match the other strategies. */
public final class CaffeineCache implements ProductCache {
    private volatile Cache<Long,Product> data = Caffeine.newBuilder().build();
    public Optional<Product> get(long id) { return Optional.ofNullable(data.getIfPresent(id)); }
    public ProductPage page(int page,int size,String search) { return ProductPage.from(data.asMap().values(),page,size,search); }
    public synchronized void replaceAll(Collection<Product> products) {
        Cache<Long,Product> next=Caffeine.newBuilder().build(); next.putAll(ProductCache.index(products)); data=next;
    }
    public synchronized void apply(Changes changes) { changes.applyTo(data.asMap()); }
    public int size() { return data.asMap().size(); }
}
