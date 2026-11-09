## 2024-05-18 - Optimize project_metrics SQLite Query
**Learning:** In `project_metrics`, we were making two separate database queries to get aggregate metric counts, resulting in N+1 overhead. We can combine multiple scalar aggregate queries into a single query using subselects inside the `SELECT` clause (e.g. `SELECT (SELECT COUNT(*) FROM a), (SELECT COUNT(*) FROM b)`), avoiding database round-trips.
**Action:** Always combine uncorrelated scalar aggregates in SQLite into a single query to eliminate database round-trips.
