"""Fixture 09: a 6 s animation with two planted glitches (a jump back at 3.0-3.2 s, one red frame at 4.5 s)."""
import subprocess, sys, tempfile
from pathlib import Path
from PIL import Image, ImageDraw

out = Path(sys.argv[1] if len(sys.argv) > 1 else "fixtures/09-anim.mp4")
fps, n, W, H = 30, 180, 640, 360
with tempfile.TemporaryDirectory() as tmp:
    for f in range(n):
        im = Image.new("RGB", (W, H), (245, 246, 248))
        d = ImageDraw.Draw(im)
        if f == 135:
            im.paste((230, 20, 20), (0, 0, W, H))
        else:
            x = 40 + (560 - 40 - 60) * f / (n - 1)
            if 90 <= f < 96:
                x = 100
            d.rounded_rectangle((x, 150, x + 60, 210), 10, fill=(36, 87, 214))
            d.text((20, 20), "Syncing payroll…", fill=(40, 40, 40))
            d.rectangle((20, 320, 20 + 600 * f / (n - 1), 330), fill=(36, 87, 214))
        im.save(f"{tmp}/{f:04d}.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", f"{tmp}/%04d.png",
                    "-pix_fmt", "yuv420p", "-c:v", "libx264", str(out)], check=True)
print(out)
