---
name: eyeproof
description: Look at what you built before you call it done, headless. Use eyeproof whenever you made or changed anything visual and must judge, verify, compare or show how it looks - a web page, UI, dashboard, chart, a browser game (canvas, WebGL, WebGPU, three.js), a Blender scene or render, a frame sequence, an animation or a video (Remotion, HyperFrames, ffmpeg, Blender); when the user says "take a screenshot", "does it look right?", "play-test it", "check the render", "visual QA", "before/after"; and before telling anyone a visual thing looks right. eyeproof renders and screenshots headless (Chromium with SwiftShader or the real GPU, Blender in the background, ffmpeg), plays games through scripted steps and records them, measures what can be measured (blank/black/magenta pixels, frozen or glitching animation, broken layout, missing textures, objects cut by the frame, console errors) and can hand the pictures to a vision model for a second opinion.
---

# eyeproof: eyes for an agent

You cannot see what you built, and most of it never appears on a screen: games run in headless Chromium,
Blender renders in the background, videos come out of ffmpeg. A desktop screenshot shows none of that. eyeproof
makes the pictures headless, measures them, and you look at them.

**First:** if `~/.config/eyeproof/LOCAL.md` exists, read it. It holds this machine's rules (when the GPU is off
limits, how to get API keys, project shortcuts) and overrides the defaults below.

Never say something "looks good", "is fixed", "animates" or "renders correctly" without an eyeproof run behind
it. When you report, quote the measured line or what you saw in the picture.

## Pick the command by what you built

| you built | run | you get |
|---|---|---|
| web page / UI | `eyeproof shot http://localhost:5173` or `page.html` | desktop + mobile PNGs, layout checks, console errors |
| browser game, canvas, WebGL/WebGPU | `eyeproof play <url> <steps…>` | shots after each input, canvas pixel checks, input-had-no-effect, frozen loop, fps |
| a game run as video | `eyeproof play <url> <steps…> --record` | `recording.webm` + video checks + sheet |
| Blender scene (.blend) | `eyeproof blend scene.blend --frames 1 60 120` | headless renders + scene checks (missing textures, no material, no light, what is in frame, what is cut) |
| render output / image sequence | `eyeproof frames out/` or `"renders/*.png"` | sheet with bad frames added, black/blank/magenta frames, frozen stretches, jumps |
| video | `eyeproof shot out/clip.mp4` | format, black stretches, frozen picture, cuts/flashes/glitches, silent or clipping audio, sheet with spike frames |
| a change | `eyeproof diff before.png after.png` | A / B / changed pixels marked, % changed and where |

Local files are served over `http://127.0.0.1` (never `file://`), so ES modules, fetch, workers and WebGPU work.
Output lands in `./.eyeproof/<time>-<cmd>/` (add `.eyeproof/` to `.gitignore`) or in `-o DIR`.

## Games: `eyeproof play`

```bash
eyeproof play "http://localhost:5173/?autoplay" \
  "until:g.ready" wait:1000 shot:start \
  key:ArrowRight:800 shot:moved "expect:g.player.x > 120" \
  burst:idle:6:250 fps "log:g.score" --gpu hw
```

Steps: `wait:MS` · `until:EXPR` · `shot:NAME` · `burst:NAME:N:MS` · `key:KEY[:HOLD_MS]` · `press:KEY` ·
`type:TEXT` · `click:X,Y|SELECTOR` · `move:X,Y` · `drag:X1,Y1,X2,Y2` · `scroll:DY` · `fps[:MS]` · `log:EXPR` ·
`expect:EXPR` · anything else is JS, awaited, with `g = window.__game` (`--hook NAME` for another global).
`--steps-file F` takes one step per line.

- **Give the game a hook.** Expose state on `window.__game` (player, score, screen, a `ready` flag). Then `until:`
  waits for real readiness instead of guessing, and `expect:` proves that input works. A scene with any animation
  always "changes" on screen, so only state proves the player moved.
- **What it measures by itself:** blank, black or magenta canvas, a canvas drawn at too low a resolution
  (blurry), nothing changed after an input, all burst frames identical (render loop dead), big jumps inside a
  burst, fps below 30, failed steps, console errors and failed requests. Warnings caused by eyeproof's own
  screenshots are filtered out, and audio autoplay is allowed.
- **`--gpu soft`** (default): SwiftShader on the CPU, WebGL + WebGPU, never touches the GPU. **`--gpu hw`**: the
  real GPU via Vulkan, WebGL + WebGPU. Use it for heavy 3D and real fps numbers. `eyeproof doctor` shows which
  renderer each mode gets.
- `--record` films the whole run (25 fps webm) and runs the video checks on it. Use it for animation, transitions
  and anything a few stills cannot show.
- Start dev servers in the background yourself, wait until the port answers, stop them afterwards.

## Blender: `eyeproof blend` and `eyeproof frames`

```bash
eyeproof blend scene.blend --frames 1 48 96 --scale 50 --samples 8     # quick check
eyeproof blend --python build_scene.py --frames 120 --engine eevee       # scene built by a script
eyeproof blend scene.blend --no-render                                   # scene checks + framing only
```
Blender runs in the background: `blender` on PATH, else the `org.blender.Blender` flatpak, or `$EYEPROOF_BLENDER`.
With the flatpak, keep the output out of `/tmp`, because the flatpak cannot see it.

Before it renders, it checks the scene:
- missing image files (render magenta)
- meshes without material
- materials with nothing connected to the output (render black)
- no light, a dark world and no emission (black frame)
- no camera, or the camera inside an object

For every frame it lists what is in view: object, share of the picture, cut at which edge. After rendering it
checks the pixels (black, blank, blown out, magenta). Blender often fails silently, with black frames or magenta
instead of an error, and these checks catch that.

If a project renders through its own scripts, check the result folder with `eyeproof frames <dir>`. Every frame is
checked, and the sheet keeps evenly spaced frames plus every bad frame and every jump. **Look at full frames for
edges, text and textures**, not only at the reduced sheet.

## Video

`eyeproof shot clip.mp4` measures over **every** frame:
- format
- black stretches
- picture frozen (identical frames)
- motion spikes: cuts, flashes, glitches, judged against the motion around them, so a camera pan does not count
- audio missing, silent or clipping, and audio/picture length mismatch

The sheet adds the frame before and at each spike. A plain 12-frame sheet misses one-frame errors. For every
spike, decide whether it is an intended cut or a bug.

## Then look yourself

`Read` the PNGs and sheets eyeproof printed. Treat measured lines as facts: fix them or explain them. Judge what
measurement cannot:
- composition, framing against the intent
- objects floating, clipping or upside down
- wrong colours, unreadable text, alignment

Then fix, run again, and `eyeproof diff` the old and new picture.

Optional second opinion from another model on OpenRouter (`OPENROUTER_API_KEY`): `--model elorian/glimpse` on
`play`, `blend` or `frames`, or `eyeproof review …` / `eyeproof look a.png --ask "…"`.

## Which eyes (benchmark in the repo, `bench/RESULTS.md`)

| | pages + video, pixels only | with eyeproof's measurements | 3D renders, pixels only | with measurements |
|---|---|---|---|---|
| Claude Opus (Read) | 88 % | **100 %** | 100 % | **100 %**, 0 invented issues |
| Claude Sonnet (Read) | 88 % | **100 %** | 100 % | 100 %, many style nitpicks |
| Glimpse (OpenRouter) | 71 % | 88 % | 60 % | 100 % |

Small, self-made benchmark (the defects were planted by the same author as the checks), so read it as a direction,
not a leaderboard.
- **If you can read images, you are the best eyes.** Use eyeproof to make and measure the pictures, then read them.
- A second model is a cheap second opinion, only together with the measurements. Never use it alone for exact
  text, fine geometry or video.

## Rules

- **Headless first.** Don't open GUI windows on the user's desktop to screenshot them. `eyeproof screen` (the real
  screen) only when the user has something open and asks you to look at it.
- `eyeproof doctor` shows ffmpeg, Chromium soft/hw (WebGL + WebGPU renderer), Blender, key.
