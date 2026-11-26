package de.backendlab.cache;
import java.util.*;
/** Deliberately broken. Never selected by the normal application profile. */
public final class UnsafeCache implements ProductCache {
    private final Map<Long,Product> data = new HashMap<>();
    public Optional<Product> get(long id) { return Optional.ofNullable(data.get(id)); }
    Collection<Product> liveValues() { return data.values(); } // package-private for controlled iterator experiment
    public ProductPage page(int page,int size,String search) { return ProductPage.from(liveValues(),page,size,search); }
    public void replaceAll(Collection<Product> products) { var next=ProductCache.index(products); data.clear(); data.putAll(next); }
    public void apply(Changes changes) { changes.applyTo(data); }
    public int size() { return data.size(); }
}
