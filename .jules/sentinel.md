
## 2024-05-23 - Fix path traversal in file export
**Vulnerability:** Path traversal in `export_memories_markdown` allowing writing files outside the intended database directory.
**Learning:** `Path.is_absolute()` check is insufficient to prevent path traversal since relative paths like `../` can bypass it.
**Prevention:** Use `pathlib.Path.resolve(strict=False)` on both target and allowed base directories, then verify `str(resolved_target).startswith(str(resolved_base) + os.sep)` and `resolved_target != resolved_base`.
