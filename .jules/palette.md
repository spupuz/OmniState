## 2024-09-23 - Broken loading states on refactored forms
**Learning:** DOM queries relying on onclick handlers break when components are refactored into accessible forms.
**Action:** Use reliable selectors (e.g. #tab-id button[type=submit]) for form-bound loading states.

## 2025-02-14 - Improve accessibility of dynamic grids and scrollable empty states
**Learning:** Dynamically generated grids mapped into DOM containers often announce as unstructured text by screen readers when native list tags are missing. Additionally, scrollable containers must have their `tabindex="0"` dynamically removed when entering an empty, non-scrollable state to prevent frustrating focus traps.
**Action:** Use `role="list"` on the static container and `role="listitem"` on the dynamic children for generic mapped grids. Use JavaScript to `removeAttribute('tabindex')` on `overflow-x-auto` elements when empty.
