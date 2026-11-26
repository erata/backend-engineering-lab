package de.backendlab.bench;
import de.backendlab.cache.*;
import org.openjdk.jmh.annotations.*;
import java.util.*;
import java.util.concurrent.TimeUnit;
/** Measures cache algorithms only, not HTTP or database. Unsafe excluded from performance rankings. */
@BenchmarkMode(Mode.Throughput)
@OutputTimeUnit(TimeUnit.SECONDS)
@Warmup(iterations=3,time=2)
@Measurement(iterations=5,time=2)
@Fork(value=2,jvmArgsAppend={"-Xms1g","-Xmx1g"})
public class CacheBenchmark {
    @State(Scope.Benchmark)
    public static class ReadState {
        @Param({"synchronized","concurrent","snapshot","caffeine"}) public String strategy;
        @Param({"100000"}) public int count;
        ProductCache cache;
        @Setup(Level.Trial) public void setup(){cache=CacheFactory.create(strategy);cache.replaceAll(ProductGenerator.generate(count));}
    }
    @State(Scope.Group)
    public static class MixedState {
        @Param({"synchronized","concurrent","snapshot","caffeine"}) public String strategy;
        @Param({"100000"}) public int count;
        ProductCache cache;
        Changes a,b;
        boolean toggle;
        @Setup(Level.Trial) public void setup(){cache=CacheFactory.create(strategy);cache.replaceAll(ProductGenerator.generate(count));
            a=Changes.upsert(java.util.stream.LongStream.rangeClosed(1,16).mapToObj(i->new Product(i,"A"+i,null)).toList());
            b=Changes.upsert(java.util.stream.LongStream.rangeClosed(1,16).mapToObj(i->new Product(i,"B"+i,null)).toList());}
    }
    @State(Scope.Thread)
    public static class Keys {
        private int index;private long[] values;
        @Setup(Level.Trial) public void setup(){var rng=new SplittableRandom(1234567);values=new long[4096];for(int i=0;i<values.length;i++)values[i]=rng.nextLong() & Long.MAX_VALUE;}
        long next(int count){return 1+(values[(index++) & (values.length-1)]%count);}
    }
    @Benchmark @Threads(4) public Optional<Product> readOnly(ReadState state,Keys keys){return state.cache.get(keys.next(state.count));}
    @Benchmark @Group("mixed") @GroupThreads(4) public Optional<Product> reader(MixedState state,Keys keys){return state.cache.get(keys.next(state.count));}
    @Benchmark @Group("mixed") @GroupThreads(1) public void writer(MixedState state){state.cache.apply(state.toggle?state.a:state.b);state.toggle=!state.toggle;}
}
