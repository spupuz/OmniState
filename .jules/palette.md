## 2024-05-24 - Interactive Non-Button Elements Need Keyboard Support
**Learning:** Binding `onclick` to non-interactive elements like `<tr>` or `<div>` (e.g. palette items) makes them completely inaccessible to keyboard and screen reader users, breaking usability and accessibility.
**Action:** Always add `tabindex="0"`, `role="button"`, focus-visible styles, and an `onkeydown` handler supporting both 'Enter' and 'Space' when creating custom interactive elements out of non-semantic tags.
