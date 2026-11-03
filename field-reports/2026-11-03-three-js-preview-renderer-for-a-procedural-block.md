# Field report: three.js preview renderer for a procedural block-style 3D asset kit

- **Project kind:** a headless three.js (WebGL) preview page that draws scene descriptions exported from a game-engine content kit (block-built animals, buildings, items, four lighting presets), used to produce documentation images
- **Agent / model:** Claude Code, Opus
- **eyeproof version:** 0.2.0
- **Commands used:** play (soft GPU, SwiftShader) with `until:` on a ready flag, JS steps to switch cameras, several `shot:` per run; around 40 runs in batches

## What eyeproof caught
- Nothing broken at the pixel level: no blank or black canvas, no console errors. That confirmed the renderer worked under SwiftShader, which was useful in itself.
- The shots made layout mistakes obvious when I looked at them: buildings facing away from the camera (blank signs), a prop placed on top of a moving belt, a row of figures cut off at the frame edges, two ears merging into one on a narrow head, a face pattern that read as a square instead of eyes. All of these came from me looking at the pictures, not from a measurement.

## False alarms
- A magenta warning fired for a scene that has an intentionally magenta shop building (a large saturated magenta block). This is correct by the rule, but there is no way to say "this colour is intended".

## What it missed
- Framing: figures were cut at the left/right edge in a line-up, and no check reported it. For canvas games there is no object list, so this is expected, but a hint like "strong non-background content touching the frame edge" would have caught it.

## Friction and bugs in eyeproof
- Many small runs in a loop (one per scene and preset). Each run starts a browser again; a batch mode with several URLs in one browser would save time.
- Nothing else; `until:` plus a ready flag in the page made the runs reliable.

## Ratings (1–5)
| usefulness | accuracy of measurements | speed | ease of use |
|---|---|---|---|
| 4 | 4 | 3 | 5 |

## Suggestions
- An option to allow a colour (e.g. `--allow-magenta` or a hex list) to silence the magenta check for intended colours.
- An edge-contact hint for canvas shots: content that differs strongly from the border background and touches the frame edge.
- Several URLs or scenes per `play` invocation, sharing one browser.
