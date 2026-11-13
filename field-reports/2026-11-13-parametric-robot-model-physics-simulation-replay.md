# Field report: parametric robot model + physics-simulation replay viewer (three.js)

- **Project kind:** parametric 3D concept model of a tracked robot in the browser (three.js, WebGL), plus a
  replay viewer for recorded rigid-body physics runs (positions/quaternions per frame, time-series chart, results table)
- **Agent / model:** Claude Code, Opus
- **eyeproof version:** 0.2.0
- **Commands used:** play (soft GPU) with `until:` readiness checks, JS steps that seek the replay timeline, `shot:` steps

## What eyeproof caught
- The decisive find was visual, not measured. Seeking a paused replay to chosen timestamps and looking at the shots
  showed that a descent controller had stood the robot vertically on its nose. In another run the robot was rocking
  back and forth at a stair edge. The numbers alone (max pitch, angular rate) pointed to "something is off" but not
  to the cause. The pictures made the cause obvious within seconds and steered the next controller change directly.
- Confirmed that the replay viewer loads and renders every run variant (no blank canvas, no console errors) before
  results were reported.

## False alarms
- The time-series chart canvas was flagged as mostly white. That is expected for a line chart on a light background.

## What it missed
- Nothing that it could reasonably have caught. The physics problems are domain problems that only a human or model
  looking at the frames can judge.

## Friction and bugs in eyeproof
- Comparing frames across timestamps needed a manual collage step: four separate full-page shots, cropped and tiled
  by hand. With a follow camera the framing also changes between shots, so before/after is harder to read.
- Hash URLs (`page.html#scene`) only work when served over HTTP, not as file paths. Easy to trip over the first time.

## Ratings (1–5)
| usefulness | accuracy of measurements | speed | ease of use |
|---|---|---|---|
| 5 | 4 | 4 | 4 |

## Suggestions
- A built-in contact sheet: `--grid` or a `sheet` command that tiles all shots of a play run, optionally cropped to
  a selector (e.g. only the 3D canvas), into one image for quick review.
- A step to crop a shot to an element (`shot:name@#canvas`) so side panels and charts do not dilute the image or the
  blank-pixel measurements.
