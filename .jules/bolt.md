## 2026-09-19 - Optimize Python chunk regex parsing
**Learning:** Using `line.startswith` is significantly faster than `re.match` for simple prefix checking, and doesn't require memory allocation. Memory constraint: `f.read().split()` is explicitly prohibited in memory instructions due to memory overhead when used on large files, so we must stick with string manipulation over generators ONLY if it avoids loading full files into memory, e.g. using `startswith` over `re.match`.
**Action:** Replace `re.match` with `line.startswith('# ')` for parsing headers.
