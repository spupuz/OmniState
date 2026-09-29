## 2024-05-15 - Pre-compile Regex and Replace re.split
**Learning:** In high-frequency Python text processing routines (e.g., tokenization in server/store.py), avoid dynamic import re and implicit regex compilation inside loops. The use of dynamic re compilation was causing a performance bottleneck, and the function was called inside loops.
**Action:** Pre-compile regular expressions at the module level using re.compile() and replace re.split() with native string operations (e.g., replace('-', '_').split('_')) for known delimiters to avoid significant overhead.
