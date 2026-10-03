## 2024-05-24 - Accessible saved searches dropdown
**Learning:** Using `<div>` and `<span>` elements with `onclick` handlers for dropdown menu items makes them inaccessible to keyboard and screen-reader users, even if they visually appear clickable.
**Action:** Always use native `<button type="button">` elements for custom dropdown menus to ensure default keyboard navigability (focus states, Enter/Space key submission) and provide descriptive `aria-label` attributes for icon-only actions (like delete buttons).
