package de.backendlab.cache;
public final class CacheFactory {
    private CacheFactory() {}
    public static ProductCache create(String strategy) {
        return switch(strategy) {
            case "unsafe" -> new UnsafeCache(); case "synchronized" -> new LockedCache();
            case "concurrent" -> new ConcurrentCache(); case "snapshot" -> new SnapshotCache();
            case "caffeine" -> new CaffeineCache(); default -> throw new IllegalArgumentException("Unknown cache: "+strategy);
        };
    }
}
