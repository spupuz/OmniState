<<<<<<< HEAD
## 2024-05-18 - Optimize project_metrics SQLite Query
**Learning:** In `project_metrics`, we were making two separate database queries to get aggregate metric counts, resulting in N+1 overhead. We can combine multiple scalar aggregate queries into a single query using subselects inside the `SELECT` clause (e.g. `SELECT (SELECT COUNT(*) FROM a), (SELECT COUNT(*) FROM b)`), avoiding database round-trips.
**Action:** Always combine uncorrelated scalar aggregates in SQLite into a single query to eliminate database round-trips.
=======
## 2024-05-18 - Avoid Python JSON Parsing on DB Rows
**Learning:** Pulling SQLite rows containing JSON strings into Python and parsing them via `json.loads()` inside a loop causes huge dictionary allocations and deserialization overhead.
**Action:** Use native SQLite JSON functions like `json_extract()` and `json_valid()` within the SQL query to push filtering and extraction to the database, drastically reducing memory bloat.
>>>>>>> origin/bolt-optimize-session-context-9444986144465825105
