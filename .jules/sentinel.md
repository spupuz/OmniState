## 2025-01-20 - [Path Traversal in Markdown Export]
**Vulnerability:** Path traversal in `export_memories_markdown` allows arbitrary file write due to insufficient sanitization of memory titles used as filenames.
**Learning:** Simple space replacement (`replace(' ', '-')`) is insufficient for sanitizing filenames derived from user-controlled input, as directory traversal sequences (`../`) remain intact.
**Prevention:** Always enforce strict allowlists for filename characters (e.g., using `re.sub(r'[^a-z0-9]+', '-', text)`) when generating filenames from dynamic input, rather than relying on denylists or partial substitutions.
