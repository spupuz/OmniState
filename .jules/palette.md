## 2024-05-24 - Dynamic empty states and scrollable containers
**Learning:** Adding `tabindex="0"` to scrollable containers is required for keyboard navigation, but when dynamic lists are empty and no longer scrollable, the `tabindex` creates an unnecessary, non-interactive focus stop which is confusing for screen reader and keyboard users.
**Action:** Always dynamically remove `tabindex="0"` from container elements when they switch to empty states that are not scrollable.
