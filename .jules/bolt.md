
## 2024-05-18 - Optimize Python SQLite Aggregation with SQL Window Functions
**Learning:** In the `Store.all_project_metrics()` method, fetching all memory rows into Python dicts to manually sort and slice the top 3 and top 8 items per project caused massive unused dictionary allocations.
**Action:** Use SQLite window functions like `ROW_NUMBER() OVER(PARTITION BY ...)` to push the sorting and top-N filtering directly to the database, completely bypassing memory bloat from unnecessary Python dictionary creation.
