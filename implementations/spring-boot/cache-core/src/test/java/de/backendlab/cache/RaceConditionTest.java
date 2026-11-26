package de.backendlab.cache;
import org.junit.jupiter.api.Test;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import static org.junit.jupiter.api.Assertions.*;
class RaceConditionTest {
    @Test void controlledLostUpdateVersusAtomicAndLock() throws Exception {
        var unsafe=new int[]{0};var barrier=new CyclicBarrier(2);
        var atomic=new AtomicInteger();var locked=new int[]{0};var lock=new Object();
        try(var pool=Executors.newFixedThreadPool(2)){
            Callable<Void> task=()->{int old=unsafe[0];barrier.await(5,TimeUnit.SECONDS);unsafe[0]=old+1;
                atomic.incrementAndGet();synchronized(lock){locked[0]++;}return null;};
            var a=pool.submit(task);var b=pool.submit(task);a.get(5,TimeUnit.SECONDS);b.get(5,TimeUnit.SECONDS);
        }
        assertEquals(1,unsafe[0],"both readers saw 0 before writing");assertEquals(2,atomic.get());assertEquals(2,locked[0]);
    }
}
