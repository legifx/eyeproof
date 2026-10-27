---
name: eyeproof
description: Look at what was built before calling it done, headless - screenshots, scripted game runs, Blender renders, frame sequences and videos, measured checks and a vision model's review. Use whenever something visual was made or changed (web page, UI, browser game, WebGL/WebGPU, Blender scene, render, animation, video), or the user asks for a screenshot, a visual check, "schau mal drüber", "sieht das gut aus?", "spiel das mal an", visual QA or before/after.
trigger: Use after building or changing a web page, UI, browser game, Blender scene, render, animation or video, or when asked to screenshot, play-test, visually check or compare something.
---

# eyeproof: eyes for an agent (headless)

You cannot see what was built, and most of it never appears on a screen: games run in headless Chromium,
Blender renders in the background, videos come out of ffmpeg. eyeproof makes the pictures headless, **measures**
them, and lets a vision model look. Never report that something "looks good", "works" or "animates" without an
eyeproof run behind it. Quote the measured line or the reviewer's finding.

The CLI is `eyeproof`; run it with the terminal tool. The vision review needs `OPENROUTER_API_KEY` in the
environment. **First:** if `~/.config/eyeproof/LOCAL.md` exists, read it. It holds this machine's rules (keys, when
the GPU is off limits) and overrides the defaults here.

## Pick the command by what was built

| built | command |
|---|---|
| web page / UI | `eyeproof review http://localhost:5173 --intent "…"` |
| browser game (canvas, WebGL, WebGPU) | `eyeproof play <url> <steps…> --model elorian/glimpse --intent "…"` |
| game as video | `eyeproof play <url> <steps…> --record` |
| Blender scene | `eyeproof blend scene.blend --frames 1 60 120 --model elorian/glimpse --intent "…"` |
| render folder / image sequence | `eyeproof frames out/ --model elorian/glimpse --intent "…"` |
| video | `eyeproof shot clip.mp4` (measurements and sheet only; do **not** ask the model about video) |
| before/after | `eyeproof diff before.png after.png` |

**Always pass `--intent`**: the reviewer judges against it.

### Game steps (`eyeproof play`)
`wait:MS` · `until:EXPR` · `shot:NAME` · `burst:NAME:N:MS` · `key:KEY[:HOLD_MS]` · `press:KEY` · `type:TEXT` ·
`click:X,Y|SELECTOR` · `move:X,Y` · `drag:X1,Y1,X2,Y2` · `scroll:DY` · `fps` · `log:EXPR` · `expect:EXPR` ·
anything else = JS with `g = window.__game`. Example:
```bash
eyeproof play "http://localhost:5173/" "until:g.ready" wait:1000 shot:start \
  key:w:1500 shot:walked "expect:g.player.x > 120" burst:idle:6:250 fps
```
- `expect:` on game state is the only proof that input works. A moving scene always "changes".
- `--gpu soft` (default, CPU) or `--gpu hw` (real GPU, WebGL + WebGPU, for heavy 3D).

## Trust order

1. **Measured findings are facts.** These include blank, black or magenta frames, a frozen render loop,
   "nothing changed after key:…", failed `expect:`, fps, missing texture files, objects without material,
   objects cut by the frame, layout overflow and console errors. Fix them, or say why they are fine.
2. **Then the model's review.** In the benchmark (`bench/RESULTS.md` in the eyeproof repo), Glimpse
   found 88–100 % of planted defects **only with these measurements**, and 60–71 % without. Its known errors:
   - it misreads typos
   - it misses stretched images and a magenta table without the measurement
   - it took a hidden table leg for a "missing" one
   - it made up problems in video
   - it sometimes loops for ~90 s without an answer
   So: "Glimpse found nothing" is not "it looks perfect". If exact text or shape matters, also open the PNG with
   your own vision tool and read it yourself.
3. **Video: measurements only.** Read the "motion spike", "frozen" and "black" lines and the sheet (spike frames
   are marked). Decide for each spike whether it is an intended cut or a glitch.

## Rules
- Don't open GUI windows on the user's desktop to screenshot them. `eyeproof screen` only when the user asks you
  to look at the screen.
- With the Blender flatpak, keep output out of `/tmp` (the flatpak cannot see it).
- Output goes to `./.eyeproof/`; keep it out of git. `eyeproof doctor` checks the install.
