## 2024-05-24 - Fix stored XSS in dashboard string escaping
**Vulnerability:** The HTML dashboard `esc()` function intended to escape double quotes to prevent XSS when inserting strings into HTML attributes, but used `replace(/"/g, '"')`, creating a no-op that left attributes vulnerable to injection.
**Learning:** Even when security logic is explicitly written and commented, small typographical errors (using a literal quote instead of an HTML entity) can completely neutralize the protection.
**Prevention:** Always verify that escaping functions emit safe entities (like `&quot;`) rather than identical characters.
