# Automated accessibility check, 28 November 2026

Lighthouse 13.5.0 in Chrome DevTools, category "Accessibility" only, navigation mode, storage not
cleared (so the page is measured logged in), in an incognito window. Docker setup of `main` at
8a35e82, demo loaded with errors E06 and S04. Only synthetic accounts and documents are shown.

| Page | Account | Desktop | Mobile | Failed | Passed | Not applicable |
| --- | --- | --- | --- | --- | --- | --- |
| Application page (`/applications/<id>`) | demo@visaassist.example | 100 | 100 | 0 | 27 | 39 |
| Findings page (`/applications/<id>/findings`), one finding | demo@visaassist.example | 100 | 100 | 0 | 24 | 42 |
| Application page with the consent card | wcag@example.com (new, no consent) | 100 | 100 | 0 | 26 | 40 |

No automated check failed, so nothing was changed in the code.

Not covered by this check (Lighthouse lists the first ten as manual checks): focusable controls,
interactive element affordance, logical tab order, visual order follows the DOM, focus traps,
managed focus, landmarks, off-screen content hidden, labels and roles of custom controls; also
keyboard-only use of every flow, a screen reader (VoiceOver), contrast in hover, focus and disabled
states, zoom to 200 % and reflow, and error messages announced to assistive technology. These are
part of the WCAG 2.2 AA audit planned for the spring; until then the system is not claimed to
conform.

The six reports are the `*.json` files in `2026-11-28/`; open one at https://googlechrome.github.io/lighthouse/viewer/.
