package de.backendlab.cache;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
/** Individual map operations are safe; pages and batches are weakly consistent. */
public final class ConcurrentCache implements ProductCache {
    private volatile Map<Long,Product> data = new ConcurrentHashMap<>();
    public Optional<Product> get(long id) { return Optional.ofNullable(data.get(id)); }
    public ProductPage page(int page,int size,String search) { return ProductPage.from(data.values(),page,size,search); }
    public synchronized void replaceAll(Collection<Product> products) { data=new ConcurrentHashMap<>(ProductCache.index(products)); }
    public synchronized void apply(Changes changes) { changes.applyTo(data); }
    public int size() { return data.size(); }
}
