# Accessibility

Automated audit with axe-core 4.10.3 (WCAG 2.0 to 2.2 A and AA rules plus best practices), run 2026-11-03 by `python scripts/a11y.py`.

| State | Viewport | Violations | Rules passed | Needs review |
|---|---|---|---|---|
| Start view | desktop | 0 | 46 | 1 |
| Island, field agent tab | desktop | 0 | 48 | 1 |
| Island, library tab | desktop | 0 | 46 | 1 |
| Credits dialog | desktop | 0 | 20 | 0 |
| Operations page | desktop | 0 | 45 | 0 |
| Educator sheet | desktop | 0 | 42 | 0 |
| Embed demo | desktop | 0 | 33 | 0 |
| Arabic interface, start view | desktop | 0 | 46 | 1 |
| Arabic interface, island | desktop | 0 | 48 | 1 |
| Start view | phone | 0 | 39 | 1 |
| Island, field agent tab | phone | 0 | 47 | 1 |
| Island, library tab | phone | 0 | 46 | 1 |
| Credits dialog | phone | 0 | 21 | 0 |
| Operations page | phone | 0 | 45 | 1 |
| Educator sheet | phone | 0 | 43 | 1 |
| Embed demo | phone | 0 | 33 | 0 |
| Arabic interface, start view | phone | 0 | 39 | 1 |
| Arabic interface, island | phone | 0 | 47 | 1 |

## Built in

- The island list is a keyboard alternative to the globe; tabs and creature switching work by keyboard.
- Motion can be paused, and `prefers-reduced-motion` starts it paused.
- Colour pairs, focus rings, forced colours and increased contrast modes are styled explicitly.
- An Arabic interface (right to left) is available from the language button. Only interface text is translated; facts, citations and source titles stay in the language of the source.
- Tables on the start view, the operations page and the educator sheet use real headers and row scopes, and plots carry text labels.
