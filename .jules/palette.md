## 2024-09-27 - Implicit Form Validation vs Blocking Alerts
**Learning:** Using JS `alert()` for form validation is a disruptive, inaccessible pattern that blocks the user's workflow. Replacing it with the native HTML5 `required` attribute allows the browser to handle the validation implicitly, providing standard, localized, and accessible tooltip feedback without disrupting the page context.
**Action:** Always prefer native HTML attributes (like `required`, `minlength`, `type="email"`) on form inputs for empty or invalid states over custom JS `alert()` logic.

## 2024-09-27 - Keyboard Navigation in Actionable Table Rows
**Learning:** While `onclick` on a `<tr>` makes rows interactive for mouse users, it completely breaks keyboard accessibility, stranding keyboard-only and screen reader users. Simply adding `tabindex="0"` allows focus, but native interaction still fails because non-interactive elements do not implicitly respond to Enter/Space.
**Action:** When a `<tr>` or non-button element is intended to be actionable, it must have `tabindex="0"`, focus-visible styles, AND an explicit `onkeydown` handler mapping the Enter and Space keys to the same action as the click.
