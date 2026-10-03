## 2024-06-25 - Using tiktoken encode_ordinary

**Learning:** `tiktoken`'s `encode` method can be significantly slower than `encode_ordinary` because it explicitly parses and rejects special tokens unless explicitly ignored. In paths that only require token counts for raw text, `encode_ordinary` provides a measurable speed boost and prevents unexpected exceptions on special token collisions (e.g. `<|endoftext|>`).
**Action:** Use `encode_ordinary` for simple token counting across strings instead of `encode` to ensure fast processing and stability against arbitrary user input.
