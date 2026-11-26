package de.backendlab.cache;
import java.util.*;
public interface ProductCache {
    Optional<Product> get(long id);
    ProductPage page(int page, int size, String search);
    void replaceAll(Collection<Product> products);
    void apply(Changes changes);
    int size();
    static Map<Long,Product> index(Collection<Product> products) {
        var result = new HashMap<Long,Product>();
        for (var p : products) if (result.put(p.id(), p) != null) throw new IllegalArgumentException("duplicate product ID");
        return result;
    }
}
