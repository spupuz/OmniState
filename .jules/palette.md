## 2024-10-25 - Dynamic Canvas ARIA Labels
**Learning:** HTML `<canvas>` elements (like those rendered by Chart.js) are opaque to screen readers, leaving data visualizations inaccessible. Static `aria-label`s on charts are insufficient because the data is dynamic.
**Action:** When rendering data to a canvas, calculate key summary points (e.g., min, max, start, end) in JavaScript and dynamically set a descriptive `aria-label` attribute on the canvas element to provide a meaningful summary of the trend to screen reader users.
