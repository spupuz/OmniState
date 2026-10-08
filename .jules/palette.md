## 2024-05-24 - Interactive button missing definition
**Learning:** Found an `onclick` binding to an undefined `reinforceMemory` function in the dashboard. While testing the UI, clicking the "👍 useful" or "⭐ important" buttons on memory entries silently failed or threw console errors because the JS implementation was missing.
**Action:** Always verify that interactive functions referenced in HTML templates are actually defined in the companion script block.
## 2024-05-24 - Seamless Feedback Mechanisms
**Learning:** Found an undefined `reinforceMemory` function on "useful/important" buttons, causing silent failures. Also observed `forgetMemory` using `prompt()`, which is a disruptive, inaccessible pattern that blocks the main thread.
**Action:** Implemented `reinforceMemory` as a seamless, one-click async action with an optimistic toast notification, avoiding native blocking prompts to keep the user workflow uninterrupted and accessible.

## 2025-02-12 - Replacing Disruptive Native Dialogs with Optimistic UI
**Learning:** Native dialogs (`confirm`, `prompt`, `alert`) severely disrupt the user experience by blocking the main thread and forcing immediate modal interaction. Additionally, in custom `toast()` implementations that append DOM elements (like an undo button), setting `textContent` on the parent node will silently wipe out the appended elements.
**Action:** Replace `confirm()` actions (like deleting items) with optimistic UI patterns where the element is immediately hidden visually, accompanied by an undo toast (using a deferred `setTimeout` for the API call). Ensure text messages in toasts use a wrapper element (like a `<span>`) to avoid overwriting functional child nodes.
