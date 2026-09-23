## 2024-09-23 - Broken loading states on refactored forms
**Learning:** DOM queries relying on onclick handlers break when components are refactored into accessible forms.
**Action:** Use reliable selectors (e.g. #tab-id button[type=submit]) for form-bound loading states.
