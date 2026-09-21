## 2026-09-21 - Accessible Canvas Charts and Actionable Empty States
**Learning:** HTML `<canvas>` elements are completely opaque to screen readers by default. Providing purely visual empty states (like "No projects") creates dead-ends for users.
**Action:** When working with `<canvas>` (like Chart.js), always compute summary statistics (e.g., min, max, top item) and apply them to a dynamic `aria-label` along with `role="img"` on the canvas element. Additionally, ensure empty states contain actionable inline commands wrapped in styled `<code>` tags to guide users on the exact next steps.
