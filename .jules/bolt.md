## 2024-10-24 - Fix N+1 query bottleneck in MCP project_list tool
**Learning:** In the OmniState backend architecture, computing expensive project metrics loop-by-loop with `store.project_metrics()` inside a list comprehension (like in the MCP server) triggers massive N+1 query bottlenecks and duplicates token counting overhead.
**Action:** Always reuse the existing TTL-cached `_project_metrics_list()` from the `App` instance to bulk-fetch precomputed metrics instead of querying the `Store` one by one.
