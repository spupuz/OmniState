## 2023-10-27 - Replace blocking prompt with custom modal
**Learning:** Using native `prompt()` for search input blocks the main thread, creates inaccessible experiences, and breaks context.
**Action:** Replace `prompt()` dialogs with custom accessible HTML modals that maintain focus control and follow the design system.
