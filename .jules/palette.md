## 2026-10-26 - Inline Feedback for Reinforce Memory Buttons
**Learning:** Relying solely on toast notifications for micro-interactions can create a disconnect. Providing temporary inline visual feedback (like changing button text and disabling it) directly on the clicked element improves user confidence.
**Action:** When implementing micro-interactions, temporarily set the button's `disabled` property to `true` and change its text/icon during the async operation, restoring the original state in a `finally` block to prevent double-clicks and ensure the UI remains interactive on failure.
