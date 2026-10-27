# eyeproof

Eyes for coding agents, headless: pictures + measured checks + optional vision-model review. Entry: README.md,
benchmark and decision: bench/RESULTS.md, state: docs/PROGRESS.md.

- Code: `web.py` (localhost server, Chromium soft/hw GPU, DOM_CHECKS, `play` step runner + recording),
  `pixels.py` (image stats/judge, sequences, diff, tiles), `video.py` (probe, motion/spikes/frozen, facts, sheets,
  frame folders), `blend.py` + `blender_inspect.py` (runs inside Blender), `look.py` (OpenRouter), `cli.py`;
  `capture.py` is only a compatibility layer for the old API (bench, tests) plus `screen`.
- Public repo: nothing machine- or person-specific in tracked files. Local rules live in
  `~/.config/eyeproof/LOCAL.md` (the skill reads it); keys only from the environment.
- Skills: `skills/install.sh` links `skills/eyeproof` into Claude Code and copies `skills/eyeproof-hermes` into
  Hermes Agent (rerun after changing the Hermes variant: Hermes rejects symlinks).
- Tests: `.venv/bin/python -m pytest -q tests` (headless Chromium, no key needed; Blender test skips without it).
- Benchmark: `OPENROUTER_API_KEY=… .venv/bin/python bench/run.py`; after editing `bench/truth.json` use
  `bench/run.py --rescore bench/runs/<run>` instead of rerunning.
- DOM checks get the configured viewport size passed in: on mobile emulation `innerWidth` grows with
  overflowing content and hides the overflow.
- Glimpse (`elorian/glimpse`) is a reasoning model: it needs a large `max_tokens` budget (24k), it rejects
  images and video in one request (look.py retries with the video alone) and sometimes loops without answering.
- Headless WebGPU needs a secure context (served http://127.0.0.1, not file://) and, for the real GPU,
  `--use-angle=vulkan --enable-features=Vulkan,WebGPU,VulkanFromANGLE,DefaultANGLEVulkan` (`web.GPU_ARGS`);
  soft mode needs `--enable-unsafe-swiftshader`.
- Video spikes are judged against the local median (±15 frames), frozen = byte-identical frames ≥ 0.5 s;
  ffmpeg's freezedetect missed/misfired on small moving objects, don't go back to it.
- Blender flatpak: absolute paths only (its cwd is /app/blender), no /tmp; script args go via $EYEPROOF_ARGS.
- Bench fixtures: `bench/make_video.py`, `bench/make_blend.py`, `bench/make_renders.py` (run inside Blender),
  `bench/fixtures/game/` (WebGL test game with `?bug=freeze|blank|deaf`).
