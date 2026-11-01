# Field report: admin dashboard view in a web app (vanilla JS SPA, forms + inline SVG line chart)

- **Project kind:** new section of an internal admin dashboard: overview tables, a settings form with side panels, a detail view with metrics and a small interactive SVG line chart. Plain JS, no framework, access gated by request headers set by a reverse proxy.
- **Agent / model:** Claude Code, Opus
- **eyeproof version:** 0.2.0
- **Commands used:** shot (desktop, --full, several URLs at once), play (soft GPU, JS steps to open a collapsed section and log element sizes)

## What eyeproof caught
- Status tags with text contrast around 2:1 (green and red text on a light tint of the same hue). Fixed with darker text, the re-run no longer reports them.
- A sticky side column taller than the viewport: "cut off at bottom … fixed, cannot be scrolled into view". The column was reused from another view where it is short. Fixed by making it static in this view.
- A small table inside a collapsible section that was wider than its column ("leaves viewport"). Root cause was an inherited global table class with a large min-width. Without this hint I would not have opened the section and found it.

## False alarms
- Header items (logo text, user name, active tab) reported at 1.20:1 contrast on every page. They sit on a translucent header and read fine in the picture; the background is probably taken from the wrong layer.
- "text overlap" between rows of a table inside a closed details element and the paragraphs below it. The table is not rendered while closed; the browser still reports stale boxes for it.

## What it missed
- The same word appeared twice in one table cell (a platform name plus a hint repeating it). I only saw this by reading the screenshot; I don't expect a checker to catch it.

## Friction and bugs in eyeproof
- No way to send request headers. The pages need auth headers on every request, so I had to write a small local proxy that injects them. A header option on shot and play would have saved that.
- shot with several URLs writes the same file names for each URL (desktop.png, desktop-part1.png, …), so later URLs overwrite earlier ones and only the last page's pictures remain. The printed list repeats the same names, which hints at it but is easy to miss.
- shot defaults to a wider desktop viewport than play, so the overflow showed up at one width and not the other. Fine once understood, but the default sizes could be printed in the report.

## Ratings (1–5)
| usefulness | accuracy of measurements | speed | ease of use |
|---|---|---|---|
| 4 | 4 | 4 | 4 |

## Suggestions
- `--header "Name: value"` (repeatable) for shot and play.
- Prefix output files with a per-URL slug or index when several URLs are given.
- Skip elements inside closed details (and content-visibility: hidden) in overlap and viewport checks, or tag those findings as "inside a collapsed element".
- Mark contrast findings on translucent or blurred backgrounds as uncertain instead of hard.
