package de.backendlab.labs.cache;

import de.backendlab.cache.Changes;
import de.backendlab.cache.ProductCache;
import de.backendlab.cache.Watermark;
import de.backendlab.catalog.ProductStore;

import java.time.Instant;
import java.util.Objects;
import java.util.concurrent.locks.ReentrantLock;

/**
 * Coordinates one cache consumer in one JVM. The scheduler and the local manual
 * endpoint share the same writer lock. This is not a distributed lock.
 */
public final class RefreshCoordinator {
    private final ProductStore store;
    private final ProductCache cache;
    private final String strategy;
    private final String sync;
    private final int batchSize;
    private final ReentrantLock writer = new ReentrantLock();

    private volatile Watermark watermark = Watermark.empty();
    private volatile State state = new State(false, null, 0, 0, null);

    private record State(boolean ready, Instant lastSuccess, long durationMillis,
                         int changes, String lastError) {}

    public record Status(boolean ready, String strategy, String sync, int products,
                         Instant lastSuccess, long durationMillis, int changes,
                         String lastError) {}

    public record RefreshResult(boolean ran, int changed, String reason) {}

    public RefreshCoordinator(ProductStore store, ProductCache cache, String strategy,
                              String sync, int batchSize) {
        this.store = Objects.requireNonNull(store);
        this.cache = Objects.requireNonNull(cache);
        this.strategy = strategy;
        this.sync = sync;
        if (!sync.equals("journal") && !sync.equals("watermark")) {
            throw new IllegalArgumentException("unknown sync strategy");
        }
        if (batchSize < 1 || batchSize > 10_000) {
            throw new IllegalArgumentException("batch size 1..10000");
        }
        this.batchSize = batchSize;
    }

    public void initialize(int seedCount) {
        writer.lock();
        long started = System.nanoTime();
        try {
            if (state.ready()) {
                throw new IllegalStateException("already initialized");
            }
            store.seedOnce(seedCount);

            // Both reads share a REPEATABLE READ snapshot. Only journal IDs
            // visible in that snapshot are acknowledged, never a range of IDs.
            var next = store.transaction(() -> {
                var products = store.all();
                var seen = store.allPendingIds();
                cache.replaceAll(products);
                store.acknowledge(seen);
                return Watermark.empty().advance(products);
            });

            watermark = next;
            // Publish readiness after successful transaction completion.
            state = new State(true, Instant.now(), elapsed(started), cache.size(), null);
        } finally {
            writer.unlock();
        }
    }

    public boolean ready() {
        return state.ready();
    }

    public Status status() {
        var s = state;
        return new Status(s.ready(), strategy, sync, cache.size(), s.lastSuccess(),
                s.durationMillis(), s.changes(), s.lastError());
    }

    public RefreshResult refresh() {
        if (!state.ready()) {
            return new RefreshResult(false, 0, "not-ready");
        }
        if (!writer.tryLock()) {
            return new RefreshResult(false, 0, "refresh-in-progress");
        }

        long started = System.nanoTime();
        try {
            int changed = sync.equals("journal") ? refreshJournal() : refreshWatermark();
            state = new State(true, Instant.now(), elapsed(started), changed, null);
            return new RefreshResult(true, changed, "completed");
        } catch (RuntimeException e) {
            var prev = state;
            state = new State(prev.ready(), prev.lastSuccess(), elapsed(started),
                    prev.changes(), e.getClass().getSimpleName());
            throw e;
        } finally {
            writer.unlock();
        }
    }

    private int refreshJournal() {
        return store.transaction(() -> {
            var events = store.pending(batchSize);
            var changes = store.currentChanges(events);
            cache.apply(changes);

            // A failed acknowledgement permits replay. Cache upserts and deletes
            // are idempotent; no exactly-once or distributed atomicity is claimed.
            store.acknowledge(events.stream().map(ProductStore.JournalEntry::changeId).toList());
            return changes.count();
        });
    }

    private int refreshWatermark() {
        // Deliberately limited baseline: ID/timestamp order is not commit order.
        var products = store.after(watermark);
        cache.apply(Changes.upsert(products));
        watermark = watermark.advance(products);
        return products.size();
    }

    private static long elapsed(long started) {
        return (System.nanoTime() - started) / 1_000_000;
    }
}
