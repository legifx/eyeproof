# Field report: server-rendered public gallery pages with a three.js model viewer

- **Project kind:** a web app's public gallery: a server-rendered grid of user-made 3D models with filters, a detail page with an interactive three.js viewer and animation buttons, and the same views inside a client-side single-page app
- **Agent / model:** Claude Code, Opus
- **eyeproof version:** 0.2.0
- **Commands used:** shot (desktop + mobile), play with until/click/move/expect steps (soft GPU)

## What eyeproof caught
- Nothing broken was flagged by the measurements themselves, but the pictures made three layout problems obvious at first look: a large empty band above the detail content (a global stylesheet gave every section element top padding), filter chips rendered as underlined links inside the single-page app, and a viewer that grew taller than the screen on wide desktops. All three were fixed and re-shot.
- `play` with `move:` plus `expect:` proved the hover preview works: an interactive WebGL viewer mounts on hover and is removed again when the pointer leaves, and the static image comes back. A screenshot alone could not have shown the teardown.
- `until:` on a class set by the viewer made the detail-page shots wait for the real 3D render instead of the fallback image.
- Console and request checks correctly reported two 401 responses in the single-page app for a signed-out visitor (expected there, so no action).

## False alarms
- Low-contrast findings at 1.20:1 for the logo word and a ghost "Sign in" button. Both render as dark text on a light background and are clearly readable in the screenshots; the check seems to pick the wrong background for these elements (possibly a layered or transparent background).
- The same shared-header contrast findings repeat on every page shot, which hides page-specific findings in the list. The nav-link findings at about 3:1 are real but belong to the shared header, not to the change under test.

## What it missed
- The empty band above the fold (about 130 px of nothing between breadcrumbs and content) was not measured. A check for unusually large empty vertical gaps inside the main content would have caught it.
- An element taller than the viewport on desktop (a square viewer) was not flagged.

## Friction and bugs in eyeproof
- None in eyeproof itself. Getting the app into a state with demo data needed a throwaway local server, which is the project's job, not eyeproof's.
- When filtering the output for page-specific findings, the repeated contrast lines had to be grepped out by hand.

## Ratings (1–5)
| usefulness | accuracy of measurements | speed | ease of use |
|---|---|---|---|
| 4 | 3 | 4 | 5 |

## Suggestions
- An option to ignore findings by selector (for a shared header), or to group identical findings across desktop and mobile into one line.
- A whitespace check: report large empty horizontal bands inside the main content area, and elements in the main content taller than the viewport.
- Re-check the contrast background detection for elements whose own background is transparent and whose parent paints the colour.
