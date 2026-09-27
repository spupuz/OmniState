## 2024-05-24 - Pre-compile regex and avoid dynamic imports in hot loops
**Learning:** In high-frequency Python text processing routines (e.g., tokenization in `server/store.py`), dynamic `import re` and implicit regex compilation inside loops (like `re.split()`) can introduce significant overhead.
**Action:** Pre-compile regular expressions at the module level using `re.compile()` and replace `re.split()` with native string operations (e.g., `replace('-', '_').split('_')`) for known delimiters when possible.
