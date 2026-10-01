## 2024-05-24 - Pre-compile Regex and Native Split in Loops
**Learning:** In high-frequency text processing functions like `_text_tokens`, using `import re` dynamically and relying on `re.findall` or `re.split` without pre-compiled regex objects causes major evaluation overhead.
**Action:** Pre-compile regular expressions using `re.compile()` at the module level. Replace `re.split()` with native string chaining like `.replace('-', '_').split('_')` for known delimiters to maximize efficiency.
