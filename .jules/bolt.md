## 2024-10-31 - [Optimize SQLite Fetch/Filter]
**Learning:** Fetching full tables from SQLite and filtering them in Python allocates large amounts of unused Python dictionaries. This causes a significant performance bottleneck on frequently polled endpoints (like dashboard metrics), especially when only a tiny subset of data is needed.
**Action:** Always prefer pushing filtering logic down to the database level via SQL (e.g., adding `WHERE` clauses) rather than returning all rows and iterating over them in Python.
