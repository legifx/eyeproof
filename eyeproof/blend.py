"""Headless Blender: measure a scene and render chosen frames, then judge the pixels."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image

from . import pixels, video

INSPECT = Path(__file__).with_name("blender_inspect.py")


def blender_cmd() -> list[str]:
    if os.environ.get("EYEPROOF_BLENDER"):
        return os.environ["EYEPROOF_BLENDER"].split()
    if shutil.which("blender"):
        return ["blender"]
    if shutil.which("flatpak") and subprocess.run(["flatpak", "info", "org.blender.Blender"],
                                                  capture_output=True).returncode == 0:
        return ["flatpak", "run", "org.blender.Blender"]
    raise RuntimeError("Blender not found (set EYEPROOF_BLENDER, install blender, or the org.blender.Blender flatpak)")


def blend(blend_file: str | None, out: Path, frames: list[int] | None = None, scale: int = 50, samples: int = 8,
          engine: str | None = None, camera: str | None = None, script: str | None = None, render: bool = True,
          timeout: int = 1800) -> dict:
    out = out.resolve()
    cmd = blender_cmd()
    if cmd[0] == "flatpak" and str(out).startswith("/tmp"):
        raise RuntimeError(f"the Blender flatpak cannot see /tmp; use an output folder under $HOME (got {out})")
    out.mkdir(parents=True, exist_ok=True)
    args = {"out": str(out), "frames": frames, "scale": scale, "samples": samples, "engine": engine,
            "camera": camera, "render": render}
    env_flag = ["--env=EYEPROOF_ARGS=" + json.dumps(args)] if cmd[0] == "flatpak" else []
    full = cmd[:2] + env_flag + cmd[2:] if cmd[0] == "flatpak" else cmd
    full += ["-b"] + ([str(Path(blend_file).resolve())] if blend_file else [])
    if script:
        full += ["--python", str(Path(script).resolve())]
    full += ["--python", str(INSPECT)]
    env = {**os.environ, "EYEPROOF_ARGS": json.dumps(args)}
    p = subprocess.run(full, capture_output=True, text=True, timeout=timeout, env=env)
    (out / "blender.log").write_text(p.stdout + p.stderr)
    rep_file = out / "blend.json"
    if not rep_file.exists():
        tail = "\n".join((p.stdout + p.stderr).strip().splitlines()[-12:])
        raise RuntimeError(f"Blender exited {p.returncode} without a report:\n{tail}")
    rep = json.loads(rep_file.read_text())
    facts = list(rep["facts"])
    errs = [l for l in (p.stdout + p.stderr).splitlines()
            if ("error" in l.lower() or "traceback" in l.lower()) and "DeprecationWarning" not in l]
    facts += [f"blender: {l.strip()[:200]}" for l in errs[:6]]
    files = []
    for f, e in rep["frames"].items():
        view = ", ".join(f"{s['object']} {s['area']:.0%}" + (f" (cut {'/'.join(s['cut'])})" if s["cut"] else "")
                         for s in e["in_view"][:6]) or "nothing"
        e["summary"] = f"frame {f}: in view {view}"
        facts += [f"frame {f}: {n}" for n in e["notes"]]
        if not e["in_view"]:
            facts.append(f"frame {f}: no mesh is in the camera's view")
        if e.get("file") and Path(e["file"]).exists():
            files.append(Path(e["file"]))
            facts += [f"frame {f}: {x}" for x in pixels.check(e["file"], "render")]
    if len(files) > 1:
        rep["sheet"] = video.grid([Image.open(f) for f in files],
                                  [f.stem for f in files], out / "sheet.png").as_posix()
    rep["files"] = [str(f) for f in files]
    rep["all_facts"] = facts
    rep_file.write_text(json.dumps(rep, indent=2))
    return rep
