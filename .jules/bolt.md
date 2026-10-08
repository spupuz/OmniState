## 2024-06-25 - Avoid String Allocations in Hot Loops
**Learning:** In high-frequency text processing loops (like `_text_tokens`), calling `.replace()` and `.split()` unconditionally creates significant overhead due to unnecessary string allocations and list creation, even when the token doesn't contain the target characters.
**Action:** Guard string mutations (like `replace` and `split`) with an early substring check (e.g., `if '-' in tok or '_' in tok:`) to bypass the allocation overhead for strings that do not require modification. This simple check can provide ~35% speedup in hot paths.
