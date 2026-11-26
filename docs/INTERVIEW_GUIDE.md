# Interview discussion prompts

Use these as discussion topics only after understanding and running the corresponding lab. Do not claim a measured result until there is an actual report.

| Question | Key explanation |
|---|---|
| Is a singleton thread-safe? | Lifetime and access safety are independent. Shared state requires appropriate synchronization or immutable publication. |
| Why is ConcurrentHashMap not a snapshot? | Single operations are safe; a multi-entry batch may be visible in stages. |
| Why does LastUpdatedTime fail? | Null values never match a simple greater-than predicate; allocated IDs and timestamps are not commit ordering. |
| Why use a journal? | Persist notifications with the DB transaction; acknowledge exact seen IDs and make replay idempotent. Single consumer only. |
| Thread vs Task? | Thread is an execution resource; Task models work/completion and need not occupy a thread while waiting. |
| Async vs parallel? | Async avoids blocked waits; parallel CPU execution runs work simultaneously. Independent I/O calls can also overlap. |
| Virtual Threads? | Lightweight thread-per-task for blocking I/O; no automatic CPU-bound speedup. Still need connection and concurrency limits. |
| Lock vs CAS? | Lock serializes a critical section; CAS retries a conditional atomic state update. Contention can hurt both. |
| Why scope a resource? | An appropriate lifetime avoids reuse of non-thread-safe contexts, leaks and unnecessary allocation. |
| Domain events vs direct calls? | Decouple side effects where useful; direct orchestration may be simpler. In-process events are not durable messages. |
| Why benchmark within one framework first? | Reduces confounding variables and makes a causal hypothesis more defensible. |
| What is the cache stampede? | Concurrent misses trigger duplicate loads; single-flight coordinates a load locally. Distributed coordination is a separate concern. |

A concise portfolio description: “I built a private product-catalogue lab to examine correctness, caching, asynchronous I/O and runtime trade-offs in Java and .NET. I compare implementations under controlled workloads and document which results were actually measured.” Use future tense for incomplete experiments.
