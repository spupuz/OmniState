## 2025-02-15 - Inconsistent Path Traversal Protection
**Vulnerability:** Path traversal in `export_memories_markdown` allowed writing files outside the intended data directory.
**Learning:** Security validations are often missed when similar functions are implemented inconsistently (e.g. `export_memories` was safe, but `export_memories_markdown` lacked the `resolve(strict=False)` check).
**Prevention:** Ensure all file I/O operations taking user input implement the same strict path validation logic, and extract this logic into a shared utility function where possible.
