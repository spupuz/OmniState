## 2024-05-18 - Implicit form submission for grouped search filters
**Learning:** Grouping advanced filter inputs (like dates or limits) outside a semantic `<form>` tag breaks the implicit submission pattern. Users expect to press `Enter` after modifying any input field (like `#search-project` or `#search-end`) to apply the filter.
**Action:** Always wrap functionally grouped inputs and actionable elements within semantic `<form>` tags rather than generic `<div>` containers to ensure keyboard accessibility and native mobile keyboard support.
