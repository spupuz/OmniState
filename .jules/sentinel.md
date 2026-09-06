## 2026-09-06 - Awk Backslash Escaping Bypass in JSON Construction
**Vulnerability:** A script intended to mitigate JSON injection via escaping failed to properly double backslashes when using `awk`'s `gsub`.
**Learning:** In `awk`, using `gsub(/\\/, "\\\\", var)` acts as a no-op due to how it parses string literals and replacement patterns. The backslashes evaluate to a single literal backslash, failing to escape trailing backslashes and leaving a JSON injection vulnerability.
**Prevention:** Always use the match reference `&` twice to double backslashes in `awk`'s `gsub` function: `gsub(/\\/, "&&", var)`.
