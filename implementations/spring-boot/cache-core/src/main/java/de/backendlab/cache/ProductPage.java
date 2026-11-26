package de.backendlab.cache;
import java.util.*;
public record ProductPage(int page, int size, long total, List<Product> items) {
    public ProductPage { items = List.copyOf(items); }
    public static ProductPage from(Collection<Product> products, int page, int size, String search) {
        if (page < 1 || size < 1 || size > 100) throw new IllegalArgumentException("page >= 1; size 1..100");
        String term = Objects.requireNonNullElse(search, "").toLowerCase(Locale.ROOT);
        var sorted = products.stream().filter(p -> p.name().toLowerCase(Locale.ROOT).contains(term))
                .sorted(Comparator.comparingLong(Product::id)).toList();
        long offset = (long)(page - 1) * size;
        int start = (int)Math.min(offset, sorted.size());
        int end = Math.min(start + size, sorted.size());
        return new ProductPage(page, size, sorted.size(), sorted.subList(start, end));
    }
}
