"""Compatibility layer: the old single-module API, now split into web / video / pixels."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .pixels import tile  # noqa: F401
from .video import duration, motion, sheet  # noqa: F401
from .web import VIEWPORTS, findings, parse_viewport, shot  # noqa: F401


def screen(out: Path) -> Path:
    """Screenshot of the real screen: grim on wlroots/niri Wayland (focused output), else Pillow's ImageGrab
    (X11, macOS, Windows)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("grim"):
        output = None
        if shutil.which("niri"):
            r = subprocess.run(["niri", "msg", "--json", "focused-output"], capture_output=True, text=True)
            if r.returncode == 0 and r.stdout.strip():
                output = json.loads(r.stdout).get("name")
        subprocess.run(["grim", *(["-o", output] if output else []), str(out)], check=True)
        return out
    from PIL import ImageGrab
    ImageGrab.grab().save(out)
    return out
