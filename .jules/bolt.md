## 2025-02-19 - Optimize SQLite Row Fetching in context_token_measure
**Learning:** Explicit dictionary instantiations and full-table fetches in SQLite row factory conversions using `self.q()` inside `context_token_measure` consume significant memory and cpu for large projects.
**Action:** To optimize performance-critical aggregation loops scanning large tables, bypass generic iterator wrappers and stream natively via `self._conn.execute()` and `.fetchmany()`, accessing `sqlite3.Row` values directly.
