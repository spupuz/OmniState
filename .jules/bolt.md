## 2025-02-20 - [O(1) Dictionary Lookup for Cached Project Metrics]
**Learning:** The dashboard already builds a full `_project_metrics_list()` using `all_project_metrics()`, which efficiently counts tokens via `tiktoken`. However, individual lookups like `project_metrics()` and `/api/projects/{name}` were re-running the expensive DB queries and token counting logic independently.
**Action:** Always prefer to extract `metrics` from the already-fetched `_project_metrics_list()` cache using an O(1) dictionary lookup keyed by project name before falling back to `store.project_metrics()`.
