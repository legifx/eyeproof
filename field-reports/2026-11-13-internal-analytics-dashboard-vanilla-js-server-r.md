# Field report: internal analytics dashboard (vanilla JS, server-rendered JSON API, SVG charts)

- **Project kind:** small internal web dashboard, no build step, hash routing, hand-drawn SVG line and scatter charts
- **Agent / model:** Claude Code, Opus
- **eyeproof version:** 0.2.0
- **Commands used:** shot (desktop + mobile) on several hash routes, before and after a fix

## What eyeproof caught
- Chart text scaled with the card width (SVG with a fixed viewBox): tiny axis labels in narrow cards, oversized labels in wide cards. Visible only in the screenshots, not in any measurement.
- Numbers with units wrapping inside table cells and KPI tiles, flagged as "text overflows box" on the first run.

## False alarms
- After the fix, three "text overflows box" findings of a few pixels remained on small pill badges; not visible in the picture.

## What it missed
- Nothing found later so far.

## Friction and bugs in eyeproof
- Shooting several hash routes of one single-page app means one call per route; each call starts a fresh browser.

## Ratings (1–5)
| usefulness | accuracy of measurements | speed | ease of use |
|---|---|---|---|
| 4 | 4 | 4 | 5 |

## Suggestions
- Accept several URLs (or hash routes) in one shot call and reuse the browser, with one output folder per route.
- Report the overflow amount threshold, so a 3 px overflow on a badge can be filtered out.
