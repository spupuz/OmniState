## 2024-05-24 - Interactive Non-Button Elements Need Keyboard Accessibility\n**Learning:** Binding `onclick` to a non-button element like a `<tr>` creates an interactive element that is inaccessible to keyboard-only and screen reader users.\n**Action:** To make these actionable elements fully accessible, they must include `tabindex="0"`, `role="button"`, focus-visible styles, and an `onkeydown` handler to execute logic on 'Enter' or 'Space' keypresses.

## 2024-05-24 - Form Context Should Read from Active View, Not Global Inputs
**Learning:** When users click to navigate into a detail view (like a specific project), global filter inputs remain empty. Forms within that local context that implicitly rely on those global inputs to derive context will silently fail.
**Action:** When a form performs an action in a drill-down view, always attempt to derive contextual metadata (like IDs or names) from the active DOM view itself (e.g. the view heading) before falling back to global filters.
