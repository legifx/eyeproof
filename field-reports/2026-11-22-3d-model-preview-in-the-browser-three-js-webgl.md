# Field report: 3D model preview in the browser (three.js, WebGL)

- **Project kind:** web-based 3D preview of generated blocky game characters (three.js, WebGL), plus a snapshot renderer that draws thumbnails through one shared WebGL context
- **Agent / model:** Claude Code, Opus
- **eyeproof version:** 0.2.0
- **Commands used:** play (soft GPU) with `until:` on a ready flag, `shot:` and one JS step that switched the animation

## What eyeproof caught
- Nothing broken this time. The run confirmed a new feature: procedural surface texture (tiled bumps with a normal map, generated per part size) drawn on the flat faces and left off the slopes, in both the interactive viewer and the snapshot path.
- The screenshot also showed a size difference between three variants of one model. The camera fits each model to the view, so only the bump density gave the scale away. A pixel check could not have told me that.

## False alarms
- None. "measured: nothing fired" matched what I saw.

## What it missed
- Nothing that surfaced later. The motion check (walk animation) was only judged from one still after switching clips. A burst would have proved the loop runs, but here the animation is covered by unit tests.

## Friction and bugs in eyeproof
- A JS step that returns nothing prints `→ None`. That is fine, but I first read it as "the call failed". A short "ok (no value)" would read more clearly.
- To look at several models side by side I wrote a throwaway HTML page and served the web root myself. The page imports modules by absolute path from the web root, and the docs do not say which folder becomes the root when you pass a local file, so I did not rely on it.
- Stopping my own helper server with a `pkill -f` pattern killed the calling shell (exit 144), because the pattern matched its own command line. This is not eyeproof's fault, but a `--serve DIR` option on `play` would avoid hand-rolled servers entirely.

## Ratings (1–5)
| usefulness | accuracy of measurements | speed | ease of use |
|---|---|---|---|
| 4 | 4 | 4 | 4 |

## Suggestions
- `play --serve <dir>`: serve a project folder as the web root (ES modules, fetch) and stop it afterwards.
- Show "ok" instead of `None` for JS steps without a return value.
- A step to grab a canvas's own `toDataURL` output would help check offscreen renderers (thumbnails) separately from the page.
