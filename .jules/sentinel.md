## 2024-05-24 - [HIGH] Path Traversal in Markdown Export
**Vulnerability:** A path traversal vulnerability existed in the `export_memories_markdown` function because the unsanitized `kind` field from the database was used to construct file paths for the exported markdown files.
**Learning:** Even internal data that seems safe (like database fields such as `kind`) can be manipulated (e.g. by other inputs or manual DB edits) and cause vulnerabilities like arbitrary file writes if used in file operations without sanitization.
**Prevention:** Always sanitize database fields or any string when constructing file paths dynamically, using explicit allowlists or regex replacement (e.g., `re.sub(r'[^a-z0-9]+', '-', text)`) before concatenation.
