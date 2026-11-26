package de.backendlab.cache;

import java.util.Collection;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Writers are serialized. Readers capture one immutable map reference and do
 * not hold the writer monitor while reading. Each nonempty batch copies the map.
 */
public final class SnapshotCache implements ProductCache {
    private final AtomicReference<Map<Long, Product>> data = new AtomicReference<>(Map.of());

    @Override
    public Optional<Product> get(long id) {
        return Optional.ofNullable(data.get().get(id));
    }

    @Override
    public ProductPage page(int page, int size, String search) {
        var view = data.get();
        return ProductPage.from(view.values(), page, size, search);
    }

    @Override
    public synchronized void replaceAll(Collection<Product> products) {
        data.set(Map.copyOf(ProductCache.index(products)));
    }

    @Override
    public synchronized void apply(Changes changes) {
        if (changes.count() == 0) {
            return;
        }
        var next = new HashMap<>(data.get());
        changes.applyTo(next);
        // Publish only after the complete new version has been constructed.
        data.set(Map.copyOf(next));
    }

    @Override
    public int size() {
        return data.get().size();
    }
}
