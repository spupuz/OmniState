## 2024-09-11 - Improve semantic structure and keyboard accessibility
**Learning:** Using heading tags (`<h3>`) for standalone numerical values without contextual text breaks the logical document outline for screen readers. While non-interactive elements usually shouldn't have `tabindex="0"`, scrollable areas like a timeline container *must* have it so keyboard-only users can focus and scroll them. Also, setting redundant `title` attributes on elements where the text is already visible in child elements causes unnecessary screen reader announcements.
**Action:** Always use `<p>` or `<span>` for numerical stats, ensure heading levels nest correctly (e.g., `<h3>` under `<h2>`), keep `tabindex="0"` on scrollable containers for keyboard accessibility, and avoid redundant ARIA or title attributes on visible text.

## 2024-09-12 - Fix heading semantics for numerical values
**Learning:** Using heading tags (e.g., `<h3>`) for standalone numerical values without contextual text breaks the logical document outline for screen readers.
**Action:** Always use `<p>` or `<span>` for numerical stats, and ensure heading levels nest correctly.
