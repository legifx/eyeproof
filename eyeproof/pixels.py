"""Measured facts about pixels: what a render, a canvas or a frame shows before anyone looks at it.

Everything here works on plain images (Pillow only), so it applies to page screenshots, canvas crops, Blender
renders, game frames and video frames alike.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat

SAMPLE_W = 320
TILE_H = 1400  # tall full-page shots are cut into tiles a model can still read  # analysis runs on a downscaled copy: fast, and blind to single-pixel noise


def _data(im: Image.Image):
    # Pillow 13 deprecates getdata() (gone in 14) in favour of get_flattened_data()
    return im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata()


def _small(im: Image.Image) -> Image.Image:
    im = im.convert("RGBA")
    if im.width > SAMPLE_W:
        im = im.resize((SAMPLE_W, max(1, round(im.height * SAMPLE_W / im.width))), Image.BILINEAR)
    return im


def stats(img: Image.Image | str | Path) -> dict:
    """Numbers about one image: brightness, spread, clipping, magenta, transparency, edges."""
    im = _small(Image.open(img) if isinstance(img, (str, Path)) else img)
    rgb, alpha = im.convert("RGB"), im.getchannel("A")
    luma = rgb.convert("L")
    px = list(_data(rgb))
    n = len(px)
    lum = list(_data(luma))
    st = ImageStat.Stat(luma)
    # Blender/game engines paint missing textures magenta (1, 0, 1); lit and shaded it stays at hue ~300°
    hsv = list(_data(rgb.convert("HSV")))
    magenta = sum(1 for h, s_, v in hsv if 200 <= h <= 225 and s_ > 110 and v > 90)
    edges = ImageStat.Stat(luma.filter(ImageFilter.FIND_EDGES)).mean[0]
    colours = len(set((r >> 4, g >> 4, b >> 4) for r, g, b in px))
    return {
        "size": list(Image.open(img).size) if isinstance(img, (str, Path)) else list(img.size),
        "mean": round(st.mean[0], 1), "std": round(st.stddev[0], 1),
        "dark": round(sum(v < 12 for v in lum) / n, 3), "bright": round(sum(v > 245 for v in lum) / n, 3),
        "magenta": round(magenta / n, 4), "transparent": round(sum(a < 10 for a in _data(alpha)) / n, 3),
        "edges": round(edges, 1), "colours": colours,
    }


def judge(s: dict, what: str = "image") -> list[str]:
    """Plain-language findings for numbers that look wrong. Empty list = nothing fired."""
    out = []
    if s["transparent"] > 0.98:
        out.append(f"{what} is fully transparent")
    elif s["std"] < 2.0 and s["colours"] <= 3:
        tone = "black" if s["mean"] < 12 else "white" if s["mean"] > 245 else f"one flat colour (luma {s['mean']})"
        out.append(f"{what} is blank: {tone}, no detail (std {s['std']})")
    elif s["dark"] > 0.92:
        out.append(f"{what} is almost all black ({s['dark']:.0%} of pixels < 12/255): missing light, camera inside "
                   f"an object or nothing rendered")
    elif s["bright"] > 0.92:
        out.append(f"{what} is almost all white ({s['bright']:.0%} blown out): over-exposed or nothing rendered")
    if s["magenta"] > 0.005:
        out.append(f"{what} has magenta pixels ({s['magenta']:.1%}): typical colour of a missing texture / material")
    if 2.0 <= s["std"] < 6 and s["edges"] < 1.5 and s["transparent"] < 0.98:
        tone = "dark" if s["mean"] < 40 else "bright" if s["mean"] > 215 else "mid-grey"
        out.append(f"{what} is nearly flat and {tone} (luma {s['mean']:.0f}, std {s['std']:.0f}, edges {s['edges']:.0f}): "
                   f"barely rendered, fogged or washed out")
    if s["bright"] > 0.25 and s["dark"] < 0.92 and s["bright"] <= 0.92:
        out.append(f"{what}: {s['bright']:.0%} of pixels blown out to white")
    return out


def check(path: str | Path, what: str | None = None) -> list[str]:
    return judge(stats(path), what or Path(path).name)


def change(a: Image.Image | str | Path, b: Image.Image | str | Path) -> float:
    """Mean absolute luma difference 0..255 between two images (downscaled, same size forced)."""
    ia = _small(Image.open(a) if isinstance(a, (str, Path)) else a).convert("L")
    ib = _small(Image.open(b) if isinstance(b, (str, Path)) else b).convert("L").resize(ia.size)
    return round(ImageStat.Stat(ImageChops.difference(ia, ib)).mean[0], 2)


def sequence(frames: list[str | Path], times: list[float] | None = None) -> dict:
    """Change between consecutive frames: frozen stretches and jumps across a render sequence or a game burst."""
    smalls = [_small(Image.open(f)).convert("L") for f in frames]
    diffs = [round(ImageStat.Stat(ImageChops.difference(a, b.resize(a.size))).mean[0], 2)
             for a, b in zip(smalls, smalls[1:])]
    label = (lambda i: f"t={times[i]:.2f}s") if times else (lambda i: Path(frames[i]).name)
    med = sorted(diffs)[len(diffs) // 2] if diffs else 0
    def local(i, half=4):
        win = diffs[max(0, i - half):i] + diffs[i + 1:i + 1 + half]
        return sorted(win)[len(win) // 2] if win else 0.0
    spikes = [f"big change between {label(i)} and {label(i + 1)} (change {d} vs around {local(i)}): cut, camera "
              f"move or glitch, look at both frames"
              for i, d in enumerate(diffs) if d > max(6 * local(i), 4.0)]
    frozen, run = [], []
    for i, d in enumerate(diffs):
        if d < 0.05:
            run.append(i)
        if (d >= 0.05 or i == len(diffs) - 1) and len(run) >= 2:
            frozen.append(f"identical frames from {label(run[0])} to {label(run[-1] + 1)}")
        if d >= 0.05:
            run = []
    return {"diffs": diffs, "median": med, "spikes": spikes, "frozen": frozen,
            "all_identical": bool(diffs) and max(diffs) < 0.05}


def diff_image(a: str | Path, b: str | Path, out: Path) -> dict:
    """Side-by-side A | B | changes (red), plus how much and where it changed."""
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ib.size != ia.size:
        ib = ib.resize(ia.size)
    d = ImageChops.difference(ia, ib).convert("L").point(lambda v: 255 if v > 24 else 0)
    changed = d.histogram()[255] / (ia.width * ia.height)
    bbox = d.getbbox()
    overlay = Image.blend(ia, Image.new("RGB", ia.size, (0, 0, 0)), 0.55)
    overlay.paste(Image.new("RGB", ia.size, (255, 40, 40)), mask=d)
    w = ia.width
    canvas = Image.new("RGB", (w * 3 + 24, ia.height + 28), (24, 24, 24))
    draw = ImageDraw.Draw(canvas)
    for k, (im, name) in enumerate(((ia, f"A {Path(a).name}"), (ib, f"B {Path(b).name}"), (overlay, "changed"))):
        canvas.paste(im, (6 + k * (w + 6), 24))
        draw.text((8 + k * (w + 6), 6), name, fill=(230, 230, 230))
    if bbox:
        x0, y0, x1, y1 = bbox
        draw.rectangle((6 + 2 * (w + 6) + x0, 24 + y0, 6 + 2 * (w + 6) + x1, 24 + y1), outline=(255, 220, 0), width=2)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    return {"out": str(out), "changed": round(changed, 4), "bbox": list(bbox) if bbox else None}


def tile(png: Path) -> list[Path]:
    im = Image.open(png)
    if im.height <= TILE_H * 1.3:
        return [png]
    tiles = []
    for i, y in enumerate(range(0, im.height, TILE_H - 100)):
        t = png.with_name(f"{png.stem}-part{i + 1}.png")
        im.crop((0, y, im.width, min(y + TILE_H, im.height))).save(t)
        tiles.append(t)
        if y + TILE_H >= im.height:
            break
    return tiles
