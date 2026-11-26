package de.backendlab.cache;
import java.util.*;
/** A single monitor protects the whole batch and page. */
public final class LockedCache implements ProductCache {
    private Map<Long,Product> data = new HashMap<>();
    public synchronized Optional<Product> get(long id) { return Optional.ofNullable(data.get(id)); }
    public synchronized ProductPage page(int page,int size,String search) { return ProductPage.from(data.values(),page,size,search); }
    public synchronized void replaceAll(Collection<Product> products) { data=ProductCache.index(products); }
    public synchronized void apply(Changes changes) { changes.applyTo(data); }
    public synchronized int size() { return data.size(); }
}
