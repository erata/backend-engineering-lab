package de.backendlab.cache;
import java.util.*;
/** A batch has one final state per product; deletion and upsert sets are disjoint. */
public record Changes(List<Product> upserts, Set<Long> deletes) {
    public Changes {
        upserts = List.copyOf(upserts); deletes = Set.copyOf(deletes);
        var ids = new HashSet<Long>();
        for (var p : upserts) if (!ids.add(p.id()) || deletes.contains(p.id())) throw new IllegalArgumentException("conflicting change IDs");
    }
    public static Changes upsert(List<Product> products) { return new Changes(products, Set.of()); }
    public int count() { return upserts.size() + deletes.size(); }
    public void applyTo(Map<Long,Product> map) {
        deletes.forEach(map::remove); upserts.forEach(p -> map.put(p.id(), p));
    }
}
