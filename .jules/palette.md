## 2024-10-24 - Fix logical document outline for stats
**Learning:** Using heading tags (e.g., `<h3>`) for standalone numerical values without contextual text breaks the logical document outline for screen readers.
**Action:** Always use `<p>` or `<span>` for numerical stats, and ensure heading levels nest correctly.
