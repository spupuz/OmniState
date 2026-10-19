## 2025-02-25 - Use encode_ordinary_batch for tiktoken loops
**Learning:** When calculating `tiktoken` counts for a large batch of text strings (such as rows fetched from SQLite), avoid calling `encode_ordinary()` iteratively inside a Python loop, as this introduces severe Python-level overhead.
**Action:** Collect the strings into a list (e.g., `[r["content"] or "" for r in rows]`) and process them using `tiktoken.get_encoding(...).encode_ordinary_batch(texts)` to delegate the loop to highly optimized, multi-threaded Rust code.
