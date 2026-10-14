
## 2024-06-25 - Async Button Feedback
**Learning:** Adding explicit loading states to asynchronous action buttons (like "Reload" or "Auto-discover") is critical to prevent user confusion and duplicate requests while waiting for network resolution.
**Action:** When creating or modifying standalone async action buttons, ensure they accept their DOM element (`this`) and use it to toggle `disabled` state and update text content during the operation, wrapping the restoration logic in a `finally` block to handle errors gracefully.
