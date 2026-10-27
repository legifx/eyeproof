# eyeproof

**Eyes for coding agents, headless.** An agent that built a web page, a browser game, a Blender scene or a video
cannot see it, and most of that work never appears on a screen: games run in headless Chromium, Blender renders in
the background, videos come out of ffmpeg. eyeproof makes the pictures itself, **measures** what can be measured,
and hands them to the agent (or to a vision model) to look at.

```text
$ eyeproof play "game/index.html?bug=freeze" until:g.ready wait:1500 key:ArrowRight:700 \
    "expect:g.player.x > 120" burst:idle:4:300
gfx: WebGL ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) …)) | WebGPU google swiftshader  (--gpu soft)
measured: 2 finding(s)
  expect failed: g.player.x > 120 (after key:ArrowRight:700)
  burst idle: all 4 frames identical over 900 ms: the scene is not animating (paused, crashed render loop or static)
```

The idea: a screenshot alone leaves the model guessing. A screenshot **plus measured facts** (the render loop
is frozen, this texture file is missing, the dialog's bottom edge is 63 px below the viewport) lets it judge
reliably. In our small benchmark the measurements raised every model's hit rate (see below).

## What it does

| command | for | measured without any model |
|---|---|---|
| `eyeproof shot URL\|page.html` | web pages, UIs | horizontal scroll, elements off-screen, fixed elements cut off, text overflow, broken images, contrast < 3:1, overlapping text, `undefined`/`NaN`/lorem ipsum, console errors, failed requests |
| `eyeproof play URL STEPS…` | browser games: canvas, WebGL, WebGPU | blank/black/magenta canvas, blurry (low-res) canvas, nothing changed after an input, `expect:` state assertions, frozen render loop, jumps, fps |
| `eyeproof play … --record` | a game run as video | everything from the video row |
| `eyeproof blend scene.blend --frames …` | Blender, headless | missing image files, meshes without material, unconnected material output, no light, no camera, camera inside an object; per frame what is in view, its share and which edge cuts it; pixel checks of the renders |
| `eyeproof frames DIR\|GLOB` | render output, image sequences | black/blank/blown-out/magenta frames, frozen stretches, jumps; sheet that keeps every bad frame |
| `eyeproof shot clip.mp4` | videos | format, black stretches, frozen picture, cuts/flashes/glitches against the local motion (a camera pan is not a spike), audio missing/silent/clipping, audio vs picture length |
| `eyeproof diff A B` | before/after | side by side, changed pixels marked, share and bounding box |
| `eyeproof review … / look …` | second opinion | sends pictures + measured facts to a vision model on OpenRouter (default `elorian/glimpse`) |
| `eyeproof screen` | the real screen | only when you ask an agent to look at your screen |
| `eyeproof doctor` | setup | ffmpeg, Chromium soft/hw with the WebGL and WebGPU renderer it gets, Blender, key |

**Browser options:** `--gpu soft` (default: SwiftShader on the CPU, WebGL + WebGPU, never touches the GPU) or
`--gpu hw` (the real GPU via Vulkan, WebGL + WebGPU). Other options: `--viewport desktop|laptop|hd|tablet|mobile|WxH`,
`--full`, `--dark`, `--click SEL`, `--wait MS`, `--root DIR`.

Local files are served over `http://127.0.0.1`, never `file://`. WebGPU needs a secure context, and ES modules,
fetch and workers break under `file://`.

**Game steps** (`eyeproof play -h`): `wait:MS` · `until:EXPR` · `shot:NAME` · `burst:NAME:N:MS` ·
`key:KEY[:HOLD_MS]` · `press:KEY` · `type:TEXT` · `click:X,Y|SELECTOR` · `move:X,Y` · `drag:…` · `scroll:DY` ·
`fps` · `log:EXPR` · `expect:EXPR` · anything else is JS with `g = window.__game`.

Expose your game's state on `window.__game` (and a `ready` flag) and `expect:` can prove that input works. A
scene with any animation always "changes" on screen, so pixels alone cannot prove the player moved.

## Install

Linux first (tested on Ubuntu with an NVIDIA GPU). Pages and games should work wherever Playwright's Chromium
runs. Blender is found as `blender` on PATH, as the `org.blender.Blender` flatpak or via `$EYEPROOF_BLENDER`.
Needs Python 3.10+ and ffmpeg.

```bash
git clone <this repo> eyeproof && cd eyeproof
uv venv .venv && uv pip install --python .venv/bin/python -e .      # or: python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m playwright install chromium
ln -sf "$PWD/.venv/bin/eyeproof" ~/.local/bin/eyeproof
eyeproof doctor
```

A vision-model review (`review`, `look`, `--model`) needs `OPENROUTER_API_KEY`. Everything else runs offline.

### Agent skill

`skills/eyeproof/SKILL.md` teaches an agent when and how to use eyeproof. `skills/install.sh` links it into Claude
Code (`~/.claude/skills/eyeproof`) and copies a variant into Hermes Agent, if those are installed. Machine-specific
rules (when the GPU is off limits, how to get keys, project shortcuts) go into `~/.config/eyeproof/LOCAL.md`. The
skill reads that file first and it never lives in the repo.

## Benchmark: who should look?

`bench/` gives every contestant the same pictures and prompt and scores which planted defects it reports.

- **Set 1:** 8 web pages (6 with 2–3 defects each, 2 clean) and a 6 s animation with two glitches, 17 defects.
- **Set 2:** 6 Blender renders (1 clean, 5 with one 3D defect each: floating table, character inside the table,
  head cut off, upside-down tree, missing texture).
- **raw** = pixels only; **tool** = plus eyeproof's measurements. Two runs each.

| | pages + video, raw | pages + video, tool | 3D, raw | 3D, tool |
|---|---|---|---|---|
| Claude Opus (Claude Code, reads the PNGs) | 88 % | **100 %** | 100 % | **100 %** |
| Claude Sonnet | 88 % | **100 %** | 100 % | 100 % |
| Glimpse (`elorian/glimpse`, OpenRouter) | 71 % | 88 % | 60 % | 100 % |

**Read this with care.** The benchmark is small, and the defects were planted by the same author who wrote the
checks, so the "tool" numbers are partly by construction. What it does show:
- the measurements help every model;
- an agent that can read images is the better eye;
- a raw video or a pixels-only review is where models miss things or invent them.

Details, failure cases and costs: [bench/RESULTS.md](bench/RESULTS.md).

```bash
OPENROUTER_API_KEY=… .venv/bin/python bench/run.py            # needs Claude Code for the Claude contestants
```

## Development

```bash
uv pip install --python .venv/bin/python pytest && .venv/bin/python -m pytest -q tests
```
The tests drive headless Chromium against `bench/fixtures/` (including a tiny WebGL game with `?bug=freeze|blank|deaf`).
The Blender test is skipped without Blender.

## License

MIT
