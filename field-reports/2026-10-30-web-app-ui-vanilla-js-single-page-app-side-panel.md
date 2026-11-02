# Field report: web app UI (vanilla JS single-page app, side panel and floating button)

- **Project kind:** browser-based creator tool with several pages; added a floating assistant button and a slide-in side panel that pushes the page on wide screens, floats on narrow ones and becomes a bottom sheet on phones. Server ran locally with a mocked AI backend.
- **Agent / model:** Claude Code, Opus
- **eyeproof version:** 0.2.0
- **Commands used:** play (soft GPU) with steps files, at three viewports (desktop, narrow laptop, phone)

## What eyeproof caught
- A new microphone button in a toolbar squeezed two neighbouring labels down to one or two letters in a docked layout. Only visible in the picture, no measurement flagged it.
- The floating button overlapped the rounded frame of a preview area by a few pixels.
- On the phone viewport the floating button covered part of a chip row; fixed with extra scroll padding at the page end.
- `log:` with `getBoundingClientRect()` of the button, the composer and the bottom navigation gave hard numbers for "does it overlap", which was more reliable than judging from the image.

## False alarms
- Every run reported one console error and one failed request (401 on the session endpoint). That was the page's first load before the steps signed in, so expected. A way to mark known requests as expected would remove the noise.

## What it missed
- Nothing found later so far. Overlap of fixed elements with buttons is not measured automatically; I had to log rects myself.

## Friction and bugs in eyeproof
- Steps that change the hash route and reload need generous `wait:` values; `until:` helped once the element existed.
- The printed summary truncates long `log:` results, so I read them from the JSON report instead.
- Starting the local server inside a test runner and stopping it again was on me; a pattern-based kill matched my own shell.

## Ratings (1–5)
| usefulness | accuracy of measurements | speed | ease of use |
|---|---|---|---|
| 5 | 4 | 4 | 4 |

## Suggestions
- A built-in check for fixed or sticky elements that cover clickable elements (buttons, links, inputs) at each shot, with the covered element named.
- An option like `--expect-request 401:/path` to silence known failed requests.
- Print full `log:` values or say where the untruncated value is in the JSON.
