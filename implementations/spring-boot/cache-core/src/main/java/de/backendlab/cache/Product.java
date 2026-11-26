package de.backendlab.cache;
import java.time.Instant;
import java.util.Objects;
public record Product(long id, String name, Instant lastUpdatedTime) {
    public Product { if (id <= 0) throw new IllegalArgumentException("id must be positive"); Objects.requireNonNull(name); }
}
