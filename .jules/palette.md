## 2024-05-24 - Interactive button missing definition
**Learning:** Found an `onclick` binding to an undefined `reinforceMemory` function in the dashboard. While testing the UI, clicking the "👍 useful" or "⭐ important" buttons on memory entries silently failed or threw console errors because the JS implementation was missing.
**Action:** Always verify that interactive functions referenced in HTML templates are actually defined in the companion script block.
## 2024-05-24 - Seamless Feedback Mechanisms
**Learning:** Found an undefined `reinforceMemory` function on "useful/important" buttons, causing silent failures. Also observed `forgetMemory` using `prompt()`, which is a disruptive, inaccessible pattern that blocks the main thread.
**Action:** Implemented `reinforceMemory` as a seamless, one-click async action with an optimistic toast notification, avoiding native blocking prompts to keep the user workflow uninterrupted and accessible.
