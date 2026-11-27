# Reports

| File / folder | Content |
|---|---|
| [BENCHMARK_REPORT.md](BENCHMARK_REPORT.md) | **Consolidated, interpreted results of all benchmarks** (start here) |
| `runs/<UTC>/` | JMH runs from `tools/run_benchmark.py`: raw JSON per workload, `environment.json`, `REPORT.md`. Only the run referenced by the report is versioned |
| `bdn-runs/<tfm>/results/` | BenchmarkDotNet exports (JSON, GitHub Markdown, HTML) |
| `http-runs/<UTC>/` | `tools/run_http_suite.py` output: one k6 summary JSON per phase × experiment, `probes.json` (correctness and CPU probes, runtime info), `environment.json`, `REPORT.md` |
| [investigations/](investigations/2026-11-27-anomalies.md) | unexpected results: reproduction, measurements, root cause, consequence |
| [observability/](observability/2026-11-27-validation.md) | metric and trace ingestion check for all three editions |
| `OFFLINE_CHECKS.txt`, `EXTENDED_CHECKS.txt`, `REPORT_TOOL_TESTS.txt` | historical dependency-free correctness output (v0.1 packaging) |

[BENCHMARK_REPORT.md §2](BENCHMARK_REPORT.md#raw-data-and-which-run-supersedes-which) lists which run folder supersedes which; superseded rows stay in the raw data but are not quoted.

Rules: keep raw files and metadata together; never replace missing numbers with estimates; mark failed or contaminated runs instead of deleting them silently (see the run notes in [BENCHMARK_REPORT.md §2](BENCHMARK_REPORT.md#2-environment-and-method)). Methodology: [docs/BENCHMARKS.md](../docs/BENCHMARKS.md), [docs/EXPERIMENT_PROTOCOL.md](../docs/EXPERIMENT_PROTOCOL.md).
