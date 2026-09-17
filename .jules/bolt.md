## 2025-05-15 - Avoid Redundant Regex Parsing
**Learning:** Extracting labels via regex on thousands of historical chunks is unnecessary when only the 5 most recent chunks need them for the UI.
**Action:** Only cache metrics and parse labels for the first 5 chunks, and use a fast path for word counts on older chunks.
