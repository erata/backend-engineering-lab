
BenchmarkDotNet v0.15.6, Windows 11 (10.0.26300.9974)
13th Gen Intel Core i7-13700H 2.40GHz, 1 CPU, 20 logical and 14 physical cores
.NET SDK 10.0.404
  [Host]     : .NET 10.0.15 (10.0.15, 10.0.1526.53008), X64 RyuJIT x86-64-v3
  DefaultJob : .NET 10.0.15 (10.0.15, 10.0.1526.53008), X64 RyuJIT x86-64-v3


 Method      | Workers | Mean      | Error     | StdDev    | Allocated |
------------ |-------- |----------:|----------:|----------:|----------:|
 **Recalculate** | **1**       | **27.466 ms** | **1.1189 ms** | **3.2990 ms** |   **1.55 KB** |
 **Recalculate** | **2**       | **14.223 ms** | **0.6225 ms** | **1.8354 ms** |   **1.81 KB** |
 **Recalculate** | **4**       |  **8.711 ms** | **0.2717 ms** | **0.7968 ms** |   **2.27 KB** |
 **Recalculate** | **8**       |  **5.269 ms** | **0.1423 ms** | **0.4197 ms** |   **3.14 KB** |
