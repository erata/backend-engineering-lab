using BenchmarkDotNet.Attributes;
using BenchmarkDotNet.Running;
BenchmarkSwitcher.FromAssembly(typeof(CpuBench).Assembly).Run(args);
[MemoryDiagnoser]
public class CpuBench {
 [Params(1,2,4,8)] public int Workers{get;set;}
 [Benchmark] public object Recalculate()=>Lab.Cpu(100000,100,Workers);
}
[MemoryDiagnoser]
public class ReservationBench {
 [Params("atomic","lock")] public string Mode{get;set;}="atomic";
 [Benchmark] public object Reserve()=>Lab.Reserve(Mode,1000,2000);
}
