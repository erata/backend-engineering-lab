package de.backendlab.bench;
import de.backendlab.experiments.Experiments;import org.openjdk.jmh.annotations.*;import java.util.concurrent.*;
/**
 * Whole-experiment timings for the portable Java kernels (Lab 02 and Lab 05).
 * The same workloads exist in BenchmarkDotNet (CpuBench, ReservationBench) so the two runtimes can be compared
 * at kernel level. Each invocation is one complete experiment, including task submission and joining.
 */
@State(Scope.Benchmark) @BenchmarkMode(Mode.AverageTime) @OutputTimeUnit(TimeUnit.MILLISECONDS) @Fork(2) @Warmup(iterations=3,time=2) @Measurement(iterations=5,time=2)
public class EngineeringBenchmark {
 ExecutorService pool;
 @Setup public void init(){pool=Executors.newFixedThreadPool(32);}@TearDown public void stop(){pool.shutdownNow();}

 /** Lab 05: 100,000 items x 100 xorshift rounds, split across N workers. */
 @State(Scope.Benchmark) public static class CpuParams { @Param({"1","2","4","8"}) public int workers; }
 @Benchmark public Object cpu(CpuParams p){return Experiments.cpu(100000,100,p.workers,pool);}

 /** Lab 02: stock 1,000, 2,000 reservation attempts. Unsafe is excluded because it is not a valid implementation. */
 @State(Scope.Benchmark) public static class ReserveParams { @Param({"atomic","lock"}) public String mode; }
 @Benchmark public Object reserve(ReserveParams p){return Experiments.reserve(p.mode,1000,2000,pool);}
}
