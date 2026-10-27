"""Video and image sequences: measured facts over every frame, and contact sheets that keep the bad frames."""
from __future__ import annotations

import glob
import json
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageStat

from . import pixels

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".exr", ".tif", ".tiff", ".bmp"}


def probe(video: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration:stream=codec_type,codec_name,width,height,avg_frame_rate,duration,nb_frames",
                        "-of", "json", str(video)], capture_output=True, text=True, check=True)
    d = json.loads(r.stdout)
    v = next((s for s in d.get("streams", []) if s["codec_type"] == "video"), {})
    a = next((s for s in d.get("streams", []) if s["codec_type"] == "audio"), None)
    num, _, den = (v.get("avg_frame_rate") or "0/1").partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 0.0
    return {"duration": float(d.get("format", {}).get("duration") or v.get("duration") or 0),
            "width": v.get("width"), "height": v.get("height"), "fps": round(fps, 3), "codec": v.get("codec_name"),
            "audio": a and {"codec": a.get("codec_name"), "duration": float(a.get("duration") or 0)},
            "video_duration": float(v.get("duration") or 0)}


def duration(video: Path) -> float:
    return probe(video)["duration"]


def local_median(diffs: list[float], i: int, half: int = 15) -> float:
    """Median change of the neighbours (±half frames, without i itself): a camera pan is judged against the
    pan around it, so only changes that stand out locally count as spikes (cuts, flashes, glitches)."""
    win = diffs[max(0, i - half):i] + diffs[i + 1:i + 1 + half]
    return sorted(win)[len(win) // 2] if win else 0.0


def events(spikes: list[dict], fps: float) -> list[str]:
    """Consecutive spike frames → one event line."""
    out, run = [], []
    for s in spikes + [None]:
        if s and run and s["frame"] - run[-1]["frame"] <= 2:
            run.append(s)
            continue
        if run:
            a, b = run[0], run[-1]
            peak = max(x["change"] for x in run)
            out.append(f"motion spike at t={a['t']}s (frame {a['frame']}, change {peak}): cut, flash or glitch"
                       if len(run) <= 2 else
                       f"sudden change {a['t']}–{b['t']}s ({len(run)} frames, peak {peak}): cut, fast move or glitch")
        run = [s] if s else []
    return out


def motion(video: Path, w: int = 160, h: int = 90, freeze_s: float = 0.5) -> dict:
    """Frame-to-frame change over the whole video. Spikes are cuts, flashes and jumps a sparse sheet misses;
    frozen = stretches of byte-identical frames (a stalled render loop, a hung game, a duplicated still)."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"scale={w}:{h},format=gray",
                        "-f", "rawvideo", "-"], capture_output=True, check=True)
    fps = probe(video)["fps"] or 30
    size = w * h
    frames = [Image.frombytes("L", (w, h), r.stdout[i:i + size]) for i in range(0, len(r.stdout) - size + 1, size)]
    diffs = [ImageStat.Stat(ImageChops.difference(a, b)).mean[0] for a, b in zip(frames, frames[1:])]
    med = sorted(diffs)[len(diffs) // 2] if diffs else 0
    spikes = [{"frame": i + 1, "t": round((i + 1) / fps, 3), "change": round(d, 1)}
              for i, d in enumerate(diffs) if d > max(6 * local_median(diffs, i), 4.0)]
    frozen, start = [], None
    for i, d in enumerate(diffs + [1.0]):  # sentinel closes a run at the end
        if d <= 0.002 and start is None:
            start = i
        elif d > 0.002 and start is not None:
            if (i - start) / fps >= freeze_s:
                frozen.append({"start": round(start / fps, 2), "end": round(i / fps, 2)})
            start = None
    return {"fps": round(fps, 2), "frames": len(frames), "median_change": round(med, 3), "spikes": spikes,
            "frozen": frozen}


def _ffmpeg_log(video: Path, *args: str) -> str:
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), *args, "-f", "null", "-"],
                          capture_output=True, text=True).stderr


def facts(video: Path, motion_info: dict | None = None) -> list[str]:
    """Everything measurable about a video, as plain lines: format, black stretches, freezes, spikes, audio."""
    p = probe(video)
    lines = [f"format: {p['width']}x{p['height']} {p['codec']} {p['fps']} fps, {p['duration']:.2f} s, "
             + (f"audio {p['audio']['codec']}" if p["audio"] else "no audio track")]
    log = _ffmpeg_log(video, "-an", "-vf", "blackdetect=d=0.04:pix_th=0.08")
    for s, e in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", log):
        lines.append(f"black from {float(s):.2f}s to {float(e):.2f}s ({float(e) - float(s):.2f}s)")
    m = motion_info or motion(video)
    for f in m["frozen"]:
        lines.append(f"picture frozen (identical frames) from {f['start']:.2f}s to {f['end']:.2f}s")
    lines += events(m["spikes"], m["fps"])
    if p["audio"]:
        vol = _ffmpeg_log(video, "-vn", "-af", "volumedetect")
        mx = re.search(r"max_volume: (-?[\d.]+) dB", vol)
        mean = re.search(r"mean_volume: (-?[\d.]+) dB", vol)
        if mx and float(mx.group(1)) < -60:
            lines.append(f"audio track is silent (max {mx.group(1)} dB)")
        elif mx:
            lines.append(f"audio level: mean {mean.group(1) if mean else '?'} dB, peak {mx.group(1)} dB"
                         + (" (clipping)" if float(mx.group(1)) >= -0.1 else ""))
        if p["video_duration"] and p["audio"]["duration"] and abs(p["audio"]["duration"] - p["video_duration"]) > 0.5:
            lines.append(f"audio is {p['audio']['duration']:.2f}s but picture {p['video_duration']:.2f}s")
    return lines


def grid(images: list[Image.Image], labels: list[str], out: Path, marked: set[int] = frozenset(),
         width: int = 480, cols: int = 4) -> Path:
    """Contact sheet: images in a grid, each with a label; marked ones in orange."""
    frames = [im.convert("RGB") for im in images]
    frames = [im.resize((width, max(2, round(im.height * width / im.width)))) for im in frames]
    fw, fh = frames[0].size
    cols = min(cols, len(frames))
    rows = -(-len(frames) // cols)
    sheet = Image.new("RGB", (cols * fw + (cols + 1) * 6, rows * (fh + 26) + 6), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    for i, (im, lab) in enumerate(zip(frames, labels)):
        x, y = 6 + (i % cols) * (fw + 6), 6 + (i // cols) * (fh + 26)
        draw.text((x + 2, y + 2), lab, fill=(255, 120, 90) if i in marked else (230, 230, 230))
        sheet.paste(im.resize((fw, fh)), (x, y + 20))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out


def sheet(video: Path, out: Path, n: int = 12, width: int = 480, cols: int = 4, spikes: bool = True) -> Path:
    """Contact sheet of n evenly spaced frames plus the frame before and at every motion spike."""
    d = duration(video)
    times = [d * (i + 0.5) / n for i in range(n)]
    marked_t = set()
    if spikes:
        m = motion(video)
        fps = m["fps"] or 30
        for s in m["spikes"][:8]:
            for t in (s["t"] - 1 / fps, s["t"]):  # the frame before the spike and the spike itself
                t = round(max(t - 0.001, 0), 3)  # accurate seek lands on the first frame at or after t
                times.append(t)
                marked_t.add(t)
        times = sorted(set(times))
    images = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, t in enumerate(times):
            f = Path(tmp) / f"{i:03d}.png"
            subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
                            "-vf", f"scale={width}:-2", "-y", str(f)], check=True)
            images.append(Image.open(f).copy())
    labels = [f"#{i + 1}  t={t:.2f}s" + ("  ! motion spike" if t in marked_t else "") for i, t in enumerate(times)]
    return grid(images, labels, out, {i for i, t in enumerate(times) if t in marked_t}, width, cols)


def collect(targets: list[str]) -> list[Path]:
    """Image files from folders, globs or paths, in natural order (frame_2 before frame_10)."""
    files: list[Path] = []
    for t in targets:
        p = Path(t).expanduser()
        if p.is_dir():
            files += [f for f in p.iterdir() if f.suffix.lower() in IMG_EXT]
        elif any(ch in t for ch in "*?["):
            files += [Path(f) for f in glob.glob(str(p)) if Path(f).suffix.lower() in IMG_EXT]
        elif p.exists():
            files.append(p)
    key = lambda f: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", f.name)]
    return sorted(set(files), key=key)


def frames_report(files: list[Path], out: Path, n: int = 16) -> dict:
    """Pixel checks on every frame of a render sequence, frozen/jump check across it, and a sheet that keeps
    evenly spaced frames plus every frame something fired on."""
    bad: dict[int, list[str]] = {}
    for i, f in enumerate(files):
        found = pixels.check(f)
        if found:
            bad[i] = found
    seq = pixels.sequence(files) if len(files) > 1 else {"spikes": [], "frozen": [], "all_identical": False, "diffs": []}
    jump_idx = {i + 1 for i, d in enumerate(seq["diffs"]) if d > max(6 * (seq.get("median") or 0), 4.0)}
    pick = {round(i * (len(files) - 1) / max(n - 1, 1)) for i in range(min(n, len(files)))}
    marked = set(bad) | jump_idx
    idx = sorted(pick | set(list(marked)[:12]))
    sheet_png = grid([Image.open(files[i]) for i in idx],
                     [f"{files[i].name}" + ("  !" if i in marked else "") for i in idx], out / "frames-sheet.png",
                     {k for k, i in enumerate(idx) if i in marked})
    facts = []
    if seq["all_identical"]:
        facts.append(f"all {len(files)} frames are identical: nothing animates")
    facts += seq["frozen"] + seq["spikes"]
    for i, found in list(bad.items())[:20]:
        facts += found
    if len(bad) > 20:
        facts.append(f"… and {len(bad) - 20} more frames with pixel findings")
    sizes = {Image.open(f).size for f in files[:200]}
    if len(sizes) > 1:
        facts.append(f"frames have different sizes: {sorted(sizes)[:4]}")
    return {"frames": len(files), "sheet": str(sheet_png), "facts": facts,
            "bad_frames": {files[i].name: v for i, v in bad.items()}}
