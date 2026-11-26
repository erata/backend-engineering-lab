package de.backendlab.cache;
import org.junit.jupiter.api.Test;
import java.time.Instant;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;
class WatermarkTest {
    @Test void nullTimestampAdvancesIdButNotTime(){
        var time=Instant.parse("2026-01-01T00:00:00Z");var initial=new Watermark(100000,time);
        var next=initial.advance(List.of(new Product(100001,"New",null),new Product(5,"Old",time.minusSeconds(1))));
        assertEquals(100001,next.id());assertEquals(time,next.timestamp());
    }
}
