## 2024-05-14 - Fix N+1 in _project_metrics_list
**Learning:** In OmniState's dashboard, loading project metrics iteratively calls `project_metrics` which executes 3 SQL queries + string splits per project, causing O(N) database operations and massive overhead as projects scale.
**Action:** Created `all_project_metrics` to bulk-fetch all memory aggregations across all projects using `GROUP BY`, turning O(N) DB queries into O(1).
