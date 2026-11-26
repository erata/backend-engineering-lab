package de.backendlab.cache;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import java.util.*;
import java.util.concurrent.*;
import static org.junit.jupiter.api.Assertions.*;
class CacheContractTest {
    @ParameterizedTest @ValueSource(strings={"unsafe","synchronized","concurrent","snapshot","caffeine"})
    void singleThreadContract(String strategy){
        var c=CacheFactory.create(strategy);c.replaceAll(ProductGenerator.generate(100_000));
        assertEquals(100_000,c.size());assertEquals(10,c.page(1,10,"").items().size());
        assertEquals(11,c.page(2,10,"").items().get(0).id());
        assertEquals(100_000,c.page(10000,10,"").items().get(9).id());
        assertTrue(c.page(Integer.MAX_VALUE,10,"").items().isEmpty());
        assertEquals(1,c.page(1,10,"PRODUCT 100000").total());
        var p=new Product(100001,"New",null);c.apply(Changes.upsert(List.of(p)));assertEquals(p,c.get(p.id()).orElseThrow());
        c.apply(new Changes(List.of(new Product(1,"Renamed",null)),Set.of(2L)));assertEquals("Renamed",c.get(1).orElseThrow().name());assertTrue(c.get(2).isEmpty());
        assertEquals(100000,c.size());assertThrows(IllegalArgumentException.class,()->c.page(0,10,""));
        assertThrows(IllegalArgumentException.class,()->c.page(1,101,""));
        assertThrows(UnsupportedOperationException.class,()->c.page(1,10,"").items().clear());
    }
    @Test void unsafeIteratorFailsWithControlledWriter() throws Exception {
        var c=new UnsafeCache();c.replaceAll(ProductGenerator.generate(10));var iterator=c.liveValues().iterator();iterator.next();
        try(var executor=Executors.newSingleThreadExecutor()){
            executor.submit(()->c.apply(Changes.upsert(List.of(new Product(11,"Inserted",null))))).get(5,TimeUnit.SECONDS);
            // Future.get establishes happens-before. This is a controlled traversal/modification failure,
            // not a claim that every concurrent HashMap traversal must throw.
            assertThrows(ConcurrentModificationException.class,iterator::next);
        }
    }
    @ParameterizedTest @ValueSource(strings={"synchronized","snapshot"})
    void atomicBatchPagesNeverMixGenerations(String strategy) throws Exception {
        var c=CacheFactory.create(strategy);c.replaceAll(generation(0));
        var start=new CountDownLatch(1);
        try(var pool=Executors.newFixedThreadPool(5)){
            var writer=pool.submit(()->{start.await();for(int i=1;i<=500;i++)c.apply(Changes.upsert(generation(i)));return null;});
            var readers=new ArrayList<Future<?>>();
            for(int t=0;t<4;t++)readers.add(pool.submit(()->{start.await();for(int i=0;i<500;i++){
                var page=c.page(1,10,"");assertEquals(10,page.total());
                assertEquals(1,page.items().stream().map(Product::name).distinct().count());
            }return null;}));
            start.countDown();writer.get(20,TimeUnit.SECONDS);for(var f:readers)f.get(20,TimeUnit.SECONDS);
        }
    }
    @ParameterizedTest @ValueSource(strings={"concurrent","caffeine"})
    void concurrentReadersAndWriterPreserveIndividualRecords(String strategy) throws Exception {
        var c=CacheFactory.create(strategy);c.replaceAll(generation(0));var start=new CountDownLatch(1);
        try(var pool=Executors.newFixedThreadPool(3)){
            var writer=pool.submit(()->{start.await();for(int i=1;i<=500;i++)c.apply(Changes.upsert(generation(i)));return null;});
            var reader=pool.submit(()->{start.await();for(int i=0;i<1000;i++){var page=c.page(1,10,"");assertEquals(10,page.items().size());assertEquals(10,page.items().stream().map(Product::id).distinct().count());}return null;});
            start.countDown();writer.get(20,TimeUnit.SECONDS);reader.get(20,TimeUnit.SECONDS);
            assertTrue(c.page(1,10,"").items().stream().allMatch(p->p.name().equals("v500")));
        }
    }
    static List<Product> generation(int version){return java.util.stream.LongStream.rangeClosed(1,10).mapToObj(id->new Product(id,"v"+version,null)).toList();}
}
