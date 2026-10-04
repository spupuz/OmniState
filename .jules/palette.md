## 2026-10-04 - Keyboard Accessibility for Hover Actions
**Learning:** Hover-revealed actions (like delete icons in saved searches) are completely inaccessible to keyboard users unless they are explicitly handled on focus.
**Action:** Always apply focus-within CSS on the parent container (.parent:focus-within .action) to reveal hidden interactive elements during keyboard navigation.
