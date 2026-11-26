```

BenchmarkDotNet v0.15.6, Windows 11 (10.0.26300.9974)
13th Gen Intel Core i7-13700H 2.40GHz, 1 CPU, 20 logical and 14 physical cores
.NET SDK 10.0.404
  [Host]     : .NET 10.0.15 (10.0.15, 10.0.1526.53008), X64 RyuJIT x86-64-v3
  DefaultJob : .NET 10.0.15 (10.0.15, 10.0.1526.53008), X64 RyuJIT x86-64-v3


```
| Method  | Mode   | Mean       | Error    | StdDev   | Median     | Allocated |
|-------- |------- |-----------:|---------:|---------:|-----------:|----------:|
| **Reserve** | **atomic** |   **166.9 μs** |  **4.87 μs** | **14.28 μs** |   **163.0 μs** |   **4.92 KB** |
| **Reserve** | **lock**   | **1,038.8 μs** | **27.68 μs** | **81.61 μs** | **1,045.9 μs** |   **6.53 KB** |
