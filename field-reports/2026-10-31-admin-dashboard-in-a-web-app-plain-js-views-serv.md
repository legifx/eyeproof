# Field report: admin dashboard in a web app (plain JS views, served by a Node backend)

- **Project kind:** new admin panel with two data tables, dropdown selectors and a background job with polling, in an
  existing single-page admin console (plain JavaScript, no framework)
- **Agent / model:** Claude Code, Opus
- **eyeproof version:** 0.2.0
- **Commands used:** shot (desktop + mobile), play (soft GPU) with click, JS steps and expect

## What eyeproof caught
- The screenshots made four small UI problems visible that tests could not show: a context size printed as "1000k"
  instead of "1M", a cost shown as "$0.0000", a filter bar from another tab still visible in the new view, and a
  status column that stayed stale after saving a setting.
- `play` with `expect:` proved the save flow end to end (pick a value in a dropdown, save, reload, check the new
  state in the DOM) instead of guessing from a still.
- No console errors and no failed requests on the new view, measured, not assumed.

## False alarms
- None noticed.

## What it missed
- Nothing found later so far.

## Friction and bugs in eyeproof
- The page sits behind header-based authentication. `shot` and `play` have no option for extra request headers,
  so a small local proxy that injects the header was needed just to take the screenshot.
- A JS step starting with `const …` failed with a SyntaxError; wrapping it in an IIFE worked. The step runner
  seems to evaluate steps as expressions; this is not mentioned in the step list.

## Ratings (1–5)
| usefulness | accuracy of measurements | speed | ease of use |
|---|---|---|---|
| 4 | 5 | 4 | 3 |

## Suggestions
- A `--header NAME:VALUE` option (repeatable) for `shot` and `play`, passed to Chromium as extra HTTP headers.
- Accept statements in JS steps (wrap them in an async function automatically), or document that a step must be an
  expression.
