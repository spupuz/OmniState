<<<<<<< HEAD
## 2024-11-08 - Fixed missing glass container and a11y label in merge modal
**Learning:** In the OmniState UI, custom HTML modals should wrap their main content in a `<div class="glass w-[92vw] max-w-md p-6 relative">` container to maintain visual consistency with the design system. Ensure these modals include a title heading whose `id` exactly matches the outer container's `aria-labelledby` attribute for screen reader accessibility. The merge modal was missing both, rendering it visually broken and breaking screen reader accessibility.
**Action:** Always verify that custom HTML modals follow the established structural and a11y patterns.
=======
## 2024-11-07 - Add missing aria-labelledby target and aria-label in merge modal
**Learning:** The merge modal was missing an `id` that matched its `aria-labelledby`, and its close button needed an `aria-label` for better accessibility.
**Action:** When adding modals with `aria-labelledby`, ensure that the `id` of the title element exactly matches the `aria-labelledby` attribute on the modal wrapper, and that icon-only or generic buttons like 'Cancel' include clear `aria-labels` explaining their specific context.
>>>>>>> origin/palette-merge-modal-a11y-3743633194837941203
