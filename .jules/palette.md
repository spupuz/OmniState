## 2024-10-24 - Async Loading States in Native JS Forms
**Learning:** When manually managing button loading states during async UI operations, always ensure the original button state (enabled status and text content) is restored within a `finally` block. This guarantees the UI remains interactive if the async operation throws an error or fails.
**Action:** Consistently apply `finally` blocks for UI state resets in all async DOM event handlers.
