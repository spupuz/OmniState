## 2024-11-04 - Optimize `Store.stats` N+1 queries
**Learning:** The `stats()` method in `Store` makes 3 separate database calls (`SELECT COUNT(*)...`) sequentially, which introduces minor N+1 query overhead. By combining them into a single query, we eliminate two round-trips to SQLite.
**Action:** When fetching multiple uncorrelated scalar aggregates, combine them into a single query via subselects like `SELECT (SELECT COUNT(*) FROM a), (SELECT COUNT(*) FROM b)` to minimize round trips.
