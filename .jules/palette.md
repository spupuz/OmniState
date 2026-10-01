## 2024-06-12 - Prevent Runtime Errors on Missing Functions
**Learning:** When replacing an outdated interaction pattern (like `alert()`) with a modern one (like `toast()`), the review tool might falsely hallucinate that the new function is undefined if it doesn't parse the file correctly. It's critical to verify the function's existence (e.g., using `grep`) before attempting to "fix" an issue that isn't real.
**Action:** Always manually confirm the existence of target functions in the codebase before implementing changes to address code review feedback about missing definitions.

## 2024-06-12 - Replacing alert() with Native Validation
**Learning:** Using `alert()` for form validation is a disruptive and inaccessible pattern that blocks user workflow.
**Action:** Prioritize replacing `alert()` with native HTML5 attributes (e.g., `required`, `minlength`, `type="email"`) on inputs to allow implicit browser validation and provide standard, localized tooltips without disrupting context.
