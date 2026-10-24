## 2024-10-24 - Async Loading States in Native HTML Modals
**Learning:** When adding loading states (e.g. disabling submit buttons and changing text) to operations inside custom HTML modals, closing the modal prematurely before awaiting the API request completely bypasses the loading feedback and causes jarring UI jumping if the API fails, as users lose their context.
**Action:** Always wrap actionable elements inside a semantic `<form>` for implicit keyboard submission, keep modals open during async calls by moving the close function into the `try` block after the await, and use a `finally` block to reliably restore the submit button's original state.

## 2026-10-24 - Inline Feedback for Copy Actions
**Learning:** Relying solely on toasts for micro-interactions like 'Copy to clipboard' creates a disconnect because the feedback is rendered far away from the user's focus point.
**Action:** Always provide inline, temporary visual feedback (like changing the button text to '✓ Copied' or adding a checkmark icon) directly on the clicked element to immediately reassure the user without requiring them to shift their gaze.
