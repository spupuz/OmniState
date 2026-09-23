## 2026-09-22 - Semantic Forms for Implicit Submission
**Learning:** In OmniState dashboard, several actionable input fields were grouped with buttons using generic `<div>` containers and `onclick` events. This prevented users from using the 'Enter' key to submit (implicit submission), which is a core expectation for keyboard accessibility and mobile usability.
**Action:** Always wrap grouped `<input>` and `<button>` elements in a semantic `<form>` element with an `onsubmit` handler (and `event.preventDefault()`) to ensure keyboard accessibility and native mobile keyboard 'Go' button support.
