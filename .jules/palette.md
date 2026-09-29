## 2024-05-18 - Interactive Table Rows
**Learning:** Binding `onclick` to a non-button element like a `<tr>` creates an interactive element that is inaccessible to keyboard-only and screen reader users.
**Action:** Always add `tabindex="0"`, focus-visible styles, and an `onkeydown` handler to execute logic on 'Enter' or 'Space' keypresses to make these actionable elements fully accessible.
