# Lab 01 — evaluation and discussion

## Problem and expected outcomes

The lab investigates an initially loaded catalogue and periodic incremental refresh. The target is a correct design with documented trade-offs, not the lowest number in a throughput table. The most important lesson is that database change detection, safe object publication and a consistent multi-record view are independent requirements.

## Qualitative comparison (design analysis, not measured ranking)

| Variant | Strength | Weakness | Appropriate use in this lab |
|---|---|---|---|
| HashMap without lock | Simple reference example | Data race; traversal and update unsafe | Negative experiment only |
| Global monitor | Easy reasoning; atomic batch and page | Readers block each other and the writer | Strong baseline; may be sufficient at low concurrency |
| ConcurrentHashMap | Safe per-key operations; no global read lock | Weak multi-record view | Valid where each product is independent |
| Immutable snapshot | Consistent batch publication and reader view | Full-map copy on refresh, transient extra memory | Default for read-oriented, consistency-sensitive pages |
| Caffeine | Established cache abstraction and potential future features | Eviction disabled; weak batch visibility; extra dependency | Library comparator, not a claim of better performance |

All five sequential cache contracts should agree. The unsafe map is expected to fail its controlled traversal experiment. Safe map strategies do not all have the same consistency contract. ConcurrentHashMap and Caffeine are not classified as broken merely because they provide weaker batch visibility. Instead compare them within their stated contract.

## Observed evidence

In the dependency-free offline run, four cache variants loaded 100,000 records, returned deterministic pagination, filtered by name and applied null-timestamp inserts, updates and deletes. The locked and snapshot variants passed the concurrent atomic-page checks. The concurrent map passed individual-record and final-state checks. A controlled structural modification invalidated an unsafe iterator. A two-worker counter experiment produced unsafe=1, locked=2, atomic=2, with expected count=2. See [raw output](../../reports/OFFLINE_CHECKS.txt).

That offline subset was originally run on Java 21 only. On 2026-11-26 the full set was executed on JDK 25: Maven unit tests (12/12, Caffeine included), the MySQL/Testcontainers integration test with journal and late commit (1/1), the HTTP contract on all three editions, and JMH plus k6 benchmarks. Measured results and their interpretation are in the [Lab 01 README](README.md#7-results). They confirm the hypotheses below: the snapshot has the cheapest reads and the most expensive batches.

## Why choose snapshot as default?

The case calls for full in-memory data and readers during periodic refresh. A snapshot makes the entire published batch visible at once and avoids holding the writer lock while readers traverse it. The design has a clear mental model. The cost is rebuilding a map proportional to catalogue size on each nonempty batch. An update-heavy or memory-constrained system may prefer a different representation. A consistent page is not necessarily worth this cost if products are independent and partial-batch visibility is acceptable.

A global monitor also satisfies the atomic-page requirement and may be simpler. Measured: it reads about 19× slower than the snapshot under 4 threads, and serializes page requests (HTTP p99 121 ms vs 18 ms at 50 pages/s), so it is only adequate at low concurrency. A sorted immutable index or incremental persistent structure could reduce page or copy cost, but would change the experiment and should be measured separately.

## Why a journal as the default synchronization strategy?

It does not require treating an auto-increment ID or wall-clock timestamp as a commit-order cursor. Exact acknowledgement of visible notifications handles out-of-order commits for the single-consumer design. It also reflects hard deletes. The cost is extra schema, write amplification, cleanup and a strict consumer boundary. If only a single application writes all products, write-through or explicit invalidation could be simpler; those alternatives are not the requested timer-driven experiment.

## Interview prompts

**What is the difference between thread safety and atomicity?** Individual operations can be safe without a sequence of operations being atomic. A concurrent map does not guarantee a multi-key refresh appears as one change to a reader.

**Why use immutable values?** Even a concurrent collection cannot protect the internal mutable fields of objects stored inside it. Replacing immutable values reduces that risk.

**Is singleton a thread-safe scope?** No. It creates one shared instance per application context, which can increase concurrent access. Synchronization and stateless design are independent decisions.

**Why is LastUpdatedTime nullable important?** NULL is not greater than a timestamp in SQL. An ID condition captures many inserts but fails if transactions commit out of ID order. A journal that re-reads current product state avoids that cursor assumption.

**When would you prefer the locked variant?** When atomic consistency is required and the workload is small enough that lock contention is negligible. Simplicity can be more valuable than speculative optimisation.

**What does JMH prove?** It measures the configured microbenchmark on the recorded environment. It does not prove HTTP scalability, production correctness or superiority over another runtime.

**What would you change for multiple application instances?** The local journal consumer design is not sufficient. Each cache instance needs a reliable way to receive changes or the system needs a shared/distributed cache and suitable invalidation. Consider consumer-specific offsets, CDC or a durable broker depending on requirements.

**What does the controlled lost update demonstrate?** Read-modify-write is not atomic. A barrier can force two readers to see the same value. A lock or atomic operation preserves both increments.
