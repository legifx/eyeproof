# eyeproof — Stand

## Status (2026-10-27)
- v0.2: headless eyes for pages, browser games (play/record, WebGL + WebGPU soft/hw), Blender (blend: scene
  inspector + renders), frame sequences, videos (spikes/frozen/black/audio), diff. 12 tests green.
- Skills: `skills/install.sh` (Claude Code link, Hermes Agent copy); local rules in `~/.config/eyeproof/LOCAL.md`.
- Benchmark (bench/RESULTS.md): Claude reading the PNGs beats Glimpse on pages, video and 3D renders; Glimpse
  only usable with eyeproof's measurements, never for video.

## Next
- Publish: squash history, create the public GitHub repo, push (renamed from eyeshot, which collides with the devDept Eyeshot CAD SDK).
- Harden on 2–3 real projects (a browser game, a Blender video) before announcing.
- Optional: Blender framing for objects crossing the camera plane (ground planes are skipped by the bbox method).

## Log
- 2026-10-27 v0.1 pages + review + benchmark; v0.2 headless focus (play, record, blend, frames, diff, video facts);
  depersonalized for a public release (local rules → ~/.config/eyeproof/LOCAL.md, install.sh, screen fallback).
