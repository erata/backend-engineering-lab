package de.backendlab.cache;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
/** Dependency-free subset; not a substitute for Maven/JUnit/Testcontainers/JMH. */
public class OfflineChecks {
    static void check(boolean condition,String message){if(!condition)throw new AssertionError(message);}
    public static void main(String[] args)throws Exception{
        for(var c:List.<ProductCache>of(new UnsafeCache(),new LockedCache(),new ConcurrentCache(),new SnapshotCache())){
            c.replaceAll(ProductGenerator.generate(100000));check(c.size()==100000,"startup");
            check(c.page(2,10,"").items().getFirst().id()==11,"pagination");
            check(c.page(1,10,"PRODUCT 100000").total()==1,"search");
            c.apply(new Changes(List.of(new Product(100001,"New",null),new Product(1,"Renamed",null)),Set.of(2L)));
            check(c.size()==100000 && c.get(100001).orElseThrow().lastUpdatedTime()==null && c.get(2).isEmpty() && c.get(1).orElseThrow().name().equals("Renamed"),"changes");
            System.out.println("PASS sequential contract: "+c.getClass().getSimpleName());
        }
        for(var c:List.<ProductCache>of(new LockedCache(),new SnapshotCache())){
            c.replaceAll(generation(0));var start=new CountDownLatch(1);
            try(var pool=Executors.newFixedThreadPool(5)){
                var writer=pool.submit(()->{start.await();for(int i=1;i<=1000;i++)c.apply(Changes.upsert(generation(i)));return null;});
                var readers=new ArrayList<Future<?>>();for(int t=0;t<4;t++)readers.add(pool.submit(()->{start.await();for(int i=0;i<1000;i++){
                    var p=c.page(1,10,"");check(p.total()==10&&p.items().stream().map(Product::name).distinct().count()==1,"mixed page");}return null;}));
                start.countDown();writer.get(20,TimeUnit.SECONDS);for(var f:readers)f.get(20,TimeUnit.SECONDS);
            }
            System.out.println("PASS concurrent atomic page: "+c.getClass().getSimpleName());
        }
        var c=new ConcurrentCache();c.replaceAll(generation(0));
        try(var pool=Executors.newFixedThreadPool(2)){
            var a=pool.submit(()->{for(int i=1;i<=1000;i++)c.apply(Changes.upsert(generation(i)));});
            var b=pool.submit(()->{for(int i=0;i<1000;i++){var p=c.page(1,10,"");check(p.items().size()==10&&p.items().stream().map(Product::id).distinct().count()==10,"weak view");}});
            a.get(20,TimeUnit.SECONDS);b.get(20,TimeUnit.SECONDS);
        }
        check(c.page(1,10,"").items().stream().allMatch(p->p.name().equals("v1000")),"final generation");
        System.out.println("PASS concurrent map individual records and final state");
        var unsafe=new UnsafeCache();unsafe.replaceAll(generation(0));var iterator=unsafe.liveValues().iterator();iterator.next();
        try(var pool=Executors.newSingleThreadExecutor()){pool.submit(()->unsafe.apply(Changes.upsert(List.of(new Product(11,"New",null))))).get(5,TimeUnit.SECONDS);}
        try{iterator.next();throw new AssertionError("expected CME");}catch(ConcurrentModificationException expected){System.out.println("PASS unsafe iterator: controlled modification detected");}
        var count=new int[]{0};var locked=new int[]{0};var lock=new Object();var atomic=new AtomicInteger();var barrier=new CyclicBarrier(2);
        try(var pool=Executors.newFixedThreadPool(2)){
            Callable<Void> task=()->{int old=count[0];barrier.await(5,TimeUnit.SECONDS);count[0]=old+1;atomic.incrementAndGet();synchronized(lock){locked[0]++;}return null;};
            var a=pool.submit(task);var b=pool.submit(task);a.get(5,TimeUnit.SECONDS);b.get(5,TimeUnit.SECONDS);
        }
        check(count[0]==1&&locked[0]==2&&atomic.get()==2,"lost update");System.out.println("PASS controlled lost update: unsafe=1, locked=2, atomic=2");
        var mark=new Watermark(100000,Instant.parse("2026-01-01T00:00:00Z"));var next=mark.advance(List.of(new Product(100001,"New",null)));
        check(next.id()==100001&&next.timestamp().equals(mark.timestamp()),"null timestamp");System.out.println("PASS null timestamp watermark logic (no database)");
        System.out.println("All dependency-free checks passed on "+Runtime.version());
    }
    static List<Product> generation(int v){return java.util.stream.LongStream.rangeClosed(1,10).mapToObj(id->new Product(id,"v"+v,null)).toList();}
}
