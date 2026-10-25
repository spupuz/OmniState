
## 2024-05-18 - Optimize Python SQLite Aggregation with SQL Window Functions
**Learning:** In the `Store.all_project_metrics()` method, fetching all memory rows into Python dicts to manually sort and slice the top 3 and top 8 items per project caused massive unused dictionary allocations.
**Action:** Use SQLite window functions like `ROW_NUMBER() OVER(PARTITION BY ...)` to push the sorting and top-N filtering directly to the database, completely bypassing memory bloat from unnecessary Python dictionary creation.

## 2024-05-18 - Batch token counting optimizations
**Learning:** Calling `tiktoken`'s `encode_ordinary()` iteratively inside a Python loop for many contexts (like calculating loaded tokens per project) introduces severe Python-level overhead.
**Action:** Collect the strings into a list and process them using `tiktoken.get_encoding(...).encode_ordinary_batch(texts)` to delegate the loop to highly optimized, multi-threaded Rust code, completely bypassing the iteration overhead in Python.
