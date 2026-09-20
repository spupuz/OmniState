## 2024-10-24 - Missing Form Labels and Keyboard Focus
**Learning:** Multiple input fields and select elements in the dashboard lacked explicit `<label>` or `aria-label` attributes, rendering them opaque to screen readers. Furthermore, interactive elements relied on default browser focus rings, which often lack sufficient contrast in dark themes.
**Action:** Always add descriptive `aria-label`s to form inputs that do not have visible text labels. Explicitly define `:focus-visible` styles with a high-contrast outline for all interactive elements to ensure clear keyboard navigation visibility.
