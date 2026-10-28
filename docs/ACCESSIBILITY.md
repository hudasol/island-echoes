# Accessibility

Automated audit with axe-core 4.10.3 (WCAG 2.0 to 2.2 A and AA rules plus best practices), run 2026-10-28 by `python scripts/a11y.py`.

| State | Viewport | Violations | Rules passed | Needs review |
|---|---|---|---|---|
| Start view | desktop | 0 | 45 | 1 |
| Island, field agent tab | desktop | 0 | 47 | 1 |
| Island, library tab | desktop | 0 | 45 | 1 |
| Credits dialog | desktop | 0 | 20 | 1 |
| Operations page | desktop | 0 | 44 | 0 |
| Start view | phone | 0 | 38 | 1 |
| Island, field agent tab | phone | 0 | 46 | 1 |
| Island, library tab | phone | 0 | 45 | 1 |
| Credits dialog | phone | 0 | 21 | 0 |
| Operations page | phone | 0 | 44 | 1 |

## Built in

- The island list is a keyboard alternative to the globe; tabs and creature switching work by keyboard.
- Motion can be paused, and `prefers-reduced-motion` starts it paused.
- Colour pairs, focus rings, forced colours and increased contrast modes are styled explicitly.
- Tables on the start view and the operations page use real headers and row scopes, and plots carry text labels.
