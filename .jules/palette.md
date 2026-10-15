
## 2024-05-24 - SPA Routing Focus Loss on Drill-down
**Learning:** When drilling down from summary lists (like Overview cards or Projects table) into detail views (like `showProject`), the previously focused element is hidden via utility classes, causing keyboard focus to drop entirely to the document `body`. This disrupts screen reader flow and keyboard navigation.
**Action:** Always add `tabindex="-1"` and `focus:outline-none` to the primary heading of the newly rendered view and explicitly call `.focus()` on it during the transition. When exiting the detail view, explicitly return focus to the parent container.
