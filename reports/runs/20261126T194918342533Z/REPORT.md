# JMH benchmark — measured local results

These are indicative measurements of these implementations on one machine, not universal framework rankings.

Run: `20261126T194918342533Z`

## Cache (Lab 01)

| Benchmark | Strategy | Products | Threads | Score | Error | Unit |
|---|---|---:|---:|---:|---:|---|
| readOnly / primary | synchronized | 100000 | 4 | 4.615e+06 | 4.563e+05 | ops/s |
| readOnly / gc.alloc.rate.norm | synchronized | 100000 | 4 | 39.98 | 0.0001097 | B/op |
| readOnly / gc.count | synchronized | 100000 | 4 | 6 | n/a | counts |
| readOnly / gc.time | synchronized | 100000 | 4 | 31 | n/a | ms |
| readOnly / primary | concurrent | 100000 | 4 | 6.28e+07 | 4.79e+06 | ops/s |
| readOnly / gc.alloc.rate.norm | concurrent | 100000 | 4 | 39.98 | 6.018e-06 | B/op |
| readOnly / gc.count | concurrent | 100000 | 4 | 78 | n/a | counts |
| readOnly / gc.time | concurrent | 100000 | 4 | 151 | n/a | ms |
| readOnly / primary | snapshot | 100000 | 4 | 8.806e+07 | 7.204e+06 | ops/s |
| readOnly / gc.alloc.rate.norm | snapshot | 100000 | 4 | 16 | 4.592e-06 | B/op |
| readOnly / gc.count | snapshot | 100000 | 4 | 44 | n/a | counts |
| readOnly / gc.time | snapshot | 100000 | 4 | 87 | n/a | ms |
| readOnly / primary | caffeine | 100000 | 4 | 4.799e+07 | 1.73e+07 | ops/s |
| readOnly / gc.alloc.rate.norm | caffeine | 100000 | 4 | 39.98 | 3.83e-05 | B/op |
| readOnly / gc.count | caffeine | 100000 | 4 | 62 | n/a | counts |
| readOnly / gc.time | caffeine | 100000 | 4 | 127 | n/a | ms |
| mixed / primary | synchronized | 100000 | 5 | 2.395e+06 | 2.539e+05 | ops/s |
| mixed / gc.alloc.rate.norm | synchronized | 100000 | 5 | 24.98 | 1.442 | B/op |
| mixed / gc.count | synchronized | 100000 | 5 | 2 | n/a | counts |
| mixed / gc.time | synchronized | 100000 | 5 | 16 | n/a | ms |
| mixed / reader | synchronized | 100000 | 5 | 1.493e+06 | 1.034e+05 | ops/s |
| mixed / writer | synchronized | 100000 | 5 | 9.019e+05 | 1.657e+05 | ops/s |
| mixed / primary | concurrent | 100000 | 5 | 3.49e+07 | 4.472e+06 | ops/s |
| mixed / gc.alloc.rate.norm | concurrent | 100000 | 5 | 39.27 | 0.01954 | B/op |
| mixed / gc.count | concurrent | 100000 | 5 | 42 | n/a | counts |
| mixed / gc.time | concurrent | 100000 | 5 | 122 | n/a | ms |
| mixed / reader | concurrent | 100000 | 5 | 3.428e+07 | 4.404e+06 | ops/s |
| mixed / writer | concurrent | 100000 | 5 | 6.151e+05 | 6.915e+04 | ops/s |
| mixed / primary | snapshot | 100000 | 5 | 4.297e+07 | 5.358e+06 | ops/s |
| mixed / gc.alloc.rate.norm | snapshot | 100000 | 5 | 21.54 | 0.3707 | B/op |
| mixed / gc.count | snapshot | 100000 | 5 | 82 | n/a | counts |
| mixed / gc.time | snapshot | 100000 | 5 | 2163 | n/a | ms |
| mixed / reader | snapshot | 100000 | 5 | 4.297e+07 | 5.358e+06 | ops/s |
| mixed / writer | snapshot | 100000 | 5 | 33.41 | 2.543 | ops/s |
| mixed / primary | caffeine | 100000 | 5 | 4.383e+07 | 5.238e+06 | ops/s |
| mixed / gc.alloc.rate.norm | caffeine | 100000 | 5 | 39.4 | 0.03723 | B/op |
| mixed / gc.count | caffeine | 100000 | 5 | 54 | n/a | counts |
| mixed / gc.time | caffeine | 100000 | 5 | 114 | n/a | ms |
| mixed / reader | caffeine | 100000 | 5 | 4.32e+07 | 5.202e+06 | ops/s |
| mixed / writer | caffeine | 100000 | 5 | 6.256e+05 | 4.03e+04 | ops/s |

Mixed group: four reader threads and one writer thread; this is not a fixed 80/20 operation ratio. Writer score counts batches, not products. Compare subgroup scores, not just aggregate throughput.

## Engineering kernels (Lab 02 / Lab 05)

| Benchmark | Params | Threads | Score | Error | Unit |
|---|---|---:|---:|---:|---|
| cpu / primary | workers=1 | 1 | 22.41 | 3.949 | ms/op |
| cpu / gc.alloc.rate.norm | workers=1 | 1 | 305.9 | 23.69 | B/op |
| cpu / gc.count | workers=1 | 1 | 0 | n/a | counts |
| cpu / primary | workers=2 | 1 | 13.33 | 1.705 | ms/op |
| cpu / gc.alloc.rate.norm | workers=2 | 1 | 827.2 | 122.3 | B/op |
| cpu / gc.count | workers=2 | 1 | 0 | n/a | counts |
| cpu / primary | workers=4 | 1 | 7.296 | 0.5615 | ms/op |
| cpu / gc.alloc.rate.norm | workers=4 | 1 | 1155 | 44.79 | B/op |
| cpu / gc.count | workers=4 | 1 | 0 | n/a | counts |
| cpu / primary | workers=8 | 1 | 5.566 | 0.4772 | ms/op |
| cpu / gc.alloc.rate.norm | workers=8 | 1 | 1839 | 35.76 | B/op |
| cpu / gc.count | workers=8 | 1 | 0 | n/a | counts |
| reserve / primary | mode=atomic | 1 | 0.8088 | 0.1137 | ms/op |
| reserve / gc.alloc.rate.norm | mode=atomic | 1 | 3.547e+05 | 6841 | B/op |
| reserve / gc.count | mode=atomic | 1 | 28 | n/a | counts |
| reserve / gc.time | mode=atomic | 1 | 58 | n/a | ms |
| reserve / primary | mode=lock | 1 | 0.8572 | 0.1007 | ms/op |
| reserve / gc.alloc.rate.norm | mode=lock | 1 | 3.618e+05 | 5601 | B/op |
| reserve / gc.count | mode=lock | 1 | 27 | n/a | counts |
| reserve / gc.time | mode=lock | 1 | 63 | n/a | ms |

Review correctness guarantees before interpreting scores. See `docs/BENCHMARKS.md`. Raw JSON and `environment.json` are stored alongside this report.
