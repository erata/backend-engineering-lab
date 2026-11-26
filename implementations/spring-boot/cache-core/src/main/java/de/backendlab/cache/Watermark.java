package de.backendlab.cache;
import java.time.Instant;
import java.util.Collection;
/** Teaching baseline only: max ID and inclusive max observed timestamp, not commit order. */
public record Watermark(long id, Instant timestamp) {
    public static Watermark empty() { return new Watermark(0, Instant.parse("1970-01-01T00:00:00Z")); }
    public Watermark advance(Collection<Product> products) {
        long nextId=id; Instant nextTime=timestamp;
        for(var p:products) { nextId=Math.max(nextId,p.id()); if(p.lastUpdatedTime()!=null && p.lastUpdatedTime().isAfter(nextTime)) nextTime=p.lastUpdatedTime(); }
        return new Watermark(nextId,nextTime);
    }
}
