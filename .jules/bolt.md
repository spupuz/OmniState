## 2024-05-24 - Pre-compile Regex and Avoid `re.split` in Hot Loops
**Learning:** In high-frequency Python text processing routines (like tokenization), dynamic `import re` and implicit regex compilation inside loops introduce measurable overhead. Moreover, using `re.split()` for known delimiters is significantly slower than using native string operations.
**Action:** Pre-compile regular expressions at the module level using `re.compile()` and replace `re.split()` with native string operations (e.g., `replace('-', '_').split('_')`) for known delimiters to avoid significant overhead.
