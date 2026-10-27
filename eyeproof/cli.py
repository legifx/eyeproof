"""eyeproof: eyes for a coding agent. Headless screenshots of what you built, measured, and looked at."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

from . import look as lk
from . import pixels, video, web

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}


def default_out(name: str) -> Path:
    return Path.cwd() / ".eyeproof" / f"{time.strftime('%Y%m%d-%H%M%S')}-{name}"


def kind(target: str) -> str:
    if "://" in target:
        return "page"
    p = Path(target.split("?")[0]).expanduser()
    if p.is_dir() and not (p / "index.html").exists():
        return "frames"
    if any(ch in target for ch in "*["):
        return "frames"
    ext = p.suffix.lower()
    if ext in IMG_EXT:
        return "image"
    if ext in lk.VIDEO_EXT:
        return "video"
    if ext == ".blend":
        return "blend"
    return "page"


def print_review(res: dict) -> None:
    r = res.get("result")
    head = f"{res['model']}  {res['seconds']}s"
    if res.get("cost_usd") is not None:
        head += f"  ${res['cost_usd']:.4f}"
    print(head)
    if not r:
        print("(reply was not JSON)\n" + res["text"][:3000])
        return
    print(f"verdict: {r.get('verdict')}  —  {r.get('summary')}")
    for i in r.get("issues", []):
        print(f"  [{i.get('severity')}] {i.get('where')}: {i.get('what')}" + (f"  → {i['fix']}" if i.get("fix") else ""))


def print_facts(facts: list[str]) -> None:
    print("measured: " + ("nothing fired" if not facts else f"{len(facts)} finding(s)"))
    for f in facts:
        print("  " + f)


def gather(args, out: Path) -> tuple[list[str], list[str], dict]:
    """Files to look at + measured facts, for any target: page, image, video, frame folder, .blend."""
    files, facts, report = [], [], {}
    for t in args.targets:
        k = kind(t)
        if k == "image":
            files.append(t)
            facts += pixels.check(t)
        elif k == "video":
            v = Path(t)
            m = video.motion(v)
            facts += [f"[{v.name}] {x}" for x in video.facts(v, m)]
            files.append(str(video.sheet(v, out / f"{v.stem}-sheet.png", n=args.frames)))
            if getattr(args, "video", False):
                files.append(t)
        elif k == "frames":
            rep = video.frames_report(video.collect([t]), out, n=args.frames)
            facts += rep["facts"]
            files.append(rep["sheet"])
            report["frames"] = rep
        elif k == "blend":
            from . import blend
            rep = blend.blend(t, out, frames=None, scale=50, samples=8)
            facts += rep["all_facts"]
            files += [rep["sheet"]] if rep.get("sheet") else rep["files"]
            report["blend"] = rep
        else:
            report = web.shot(t, out, viewports=args.viewport, full=args.full, wait_ms=args.wait, dark=args.dark,
                              click=args.click, gpu=args.gpu, root=args.root)
            for s in report["shots"].values():
                files += s["files"]
            facts += web.findings(report)
    return files, web.dedupe(facts), report


def maybe_review(args, files: list[str], facts: list[str], out: Path) -> None:
    """--model given: hand pictures + measured facts to a vision model."""
    model = getattr(args, "model", None)
    if not model or model == "none" or not files:
        return
    prompt = lk.build_prompt(getattr(args, "intent", None), getattr(args, "ask", None), "\n".join(facts) or None)
    res = lk.look(files[:12], prompt, model=model)
    res.update(files=files, facts=facts)
    (out / "review.json").write_text(json.dumps(res, indent=2))
    print_review(res)


def cmd_shot(args) -> int:
    out = Path(args.out) if args.out else default_out("shot")
    out.mkdir(parents=True, exist_ok=True)
    files, facts, report = gather(args, out)
    (out / "report.json").write_text(json.dumps({**report, "facts": facts}, indent=2))
    if args.json:
        print(json.dumps({**report, "files": files, "facts": facts}, indent=2))
        return 0
    print("\n".join(files))
    print_facts(facts)
    return 0


def cmd_review(args) -> int:
    out = Path(args.out) if args.out else default_out("review")
    out.mkdir(parents=True, exist_ok=True)
    files, facts, _ = gather(args, out)
    print("looking at:\n  " + "\n  ".join(files))
    print_facts(facts)
    if args.model == "none":
        print("model: none — Read the files above yourself and judge them against the intent.")
        return 0
    maybe_review(args, files, facts, out)
    return 0


def cmd_play(args) -> int:
    out = Path(args.out) if args.out else default_out("play")
    steps = list(args.steps)
    if args.steps_file:
        steps = Path(args.steps_file).read_text().splitlines() + steps
    if not steps:
        steps = ["wait:1000", "shot:start", "burst:idle:6:250"]
    rep = web.play(args.target, steps, out, viewport=args.viewport, wait_ms=args.wait, gpu=args.gpu,
                   hook=args.hook, record=args.record, root=args.root, dark=args.dark)
    if args.json:
        print(json.dumps(rep, indent=2))
        return 0
    print(f"gfx: WebGL {rep['gfx']['webgl']} | WebGPU {rep['gfx']['webgpu']}  (--gpu {args.gpu})")
    for s in rep["steps"]:
        if "value" in s or "error" in s:
            print(f"  {s['step']}  →  {s.get('value', 'ERROR ' + str(s.get('error')))}")
    files = [s["file"] for s in rep["shots"]]
    facts = list(rep["facts"])
    if rep.get("video"):
        v = Path(rep["video"])
        m = video.motion(v)
        facts += [f"[recording] {x}" for x in video.facts(v, m)]
        sheet = video.sheet(v, out / "recording-sheet.png", n=args.frames)
        files.append(str(sheet))
        print(f"recording: {v}")
    if len(rep["shots"]) > 4:
        from PIL import Image
        g = video.grid([Image.open(s["file"]) for s in rep["shots"]], [s["name"] for s in rep["shots"]],
                       out / "shots-sheet.png")
        print(f"sheet: {g}")
    print("\n".join(files))
    print_facts(facts)
    maybe_review(args, files, facts, out)
    return 0


def cmd_frames(args) -> int:
    out = Path(args.out) if args.out else default_out("frames")
    out.mkdir(parents=True, exist_ok=True)
    files = video.collect(args.targets)
    if not files:
        raise RuntimeError("no image files found in " + " ".join(args.targets))
    rep = video.frames_report(files, out, n=args.frames)
    print(f"{rep['frames']} frames → {rep['sheet']}")
    print_facts(rep["facts"])
    maybe_review(args, [rep["sheet"]], rep["facts"], out)
    return 0


def cmd_blend(args) -> int:
    from . import blend
    out = Path(args.out) if args.out else default_out("blend")
    rep = blend.blend(args.file, out, frames=args.frames, scale=args.scale, samples=args.samples,
                      engine=args.engine, camera=args.camera, script=args.python, render=not args.no_render)
    r = rep["render"]
    print(f"Blender {rep['blender']} · {r['engine']} · {r['resolution'][0]}x{r['resolution'][1]} @ {r['percent']}% · "
          f"{r['fps']:g} fps · frames {r['frames'][0]}–{r['frames'][1]} · camera {r['camera']}")
    print(f"light: {rep['light']['lights']} lamp(s), world strength {rep['light']['world_strength']:.2f}"
          + (", emission" if rep["light"]["emission"] else ""))
    for f, e in rep["frames"].items():
        print(f"  {e['summary']}" + (f"  [{e['seconds']}s]" if e.get("seconds") is not None else ""))
    print("\n".join(rep["files"] + ([rep["sheet"]] if rep.get("sheet") else [])))
    print_facts(rep["all_facts"])
    maybe_review(args, [rep["sheet"]] if rep.get("sheet") else rep["files"], rep["all_facts"], out)
    return 0


def cmd_diff(args) -> int:
    out = Path(args.out or default_out("diff").with_suffix(".png"))
    r = pixels.diff_image(args.a, args.b, out)
    where = f" in box {r['bbox']}" if r["bbox"] else ""
    print(f"{r['out']}\nchanged: {r['changed']:.2%} of pixels{where}")
    return 0


def cmd_look(args) -> int:
    prompt = lk.build_prompt(args.intent, args.ask)
    res = lk.look(args.files, prompt, model=args.model)
    print_review(res) if not args.json else print(json.dumps(res, indent=2))
    return 0


def cmd_sheet(args) -> int:
    out = Path(args.out or Path(args.video).with_suffix(".sheet.png"))
    print(video.sheet(Path(args.video), out, n=args.frames, spikes=not args.no_spikes))
    return 0


def cmd_screen(args) -> int:
    from .capture import screen
    print(screen(Path(args.out or default_out("screen").with_suffix(".png"))))
    return 0


def cmd_doctor(args) -> int:
    ok = True
    for tool in ("ffmpeg", "ffprobe"):
        print(f"{tool:10} {'ok' if shutil.which(tool) else 'missing'}")
    for gpu in ("soft", "hw"):
        try:
            with web.serve(str(Path(__file__).with_name("__init__.py").parent)) as url, web.browser(gpu) as b:
                s = web.Session(b, "laptop")
                s.goto(url, 0)
                g = s.gfx()
                print(f"{'gpu ' + gpu:10} WebGL {g['webgl'][:70]} | WebGPU {g['webgpu']}")
                s.ctx.close()
        except Exception as e:
            ok = gpu != "soft" and ok
            print(f"{'gpu ' + gpu:10} FAIL {str(e).splitlines()[0][:150]}")
    try:
        from . import blend
        print(f"{'blender':10} {' '.join(blend.blender_cmd())}")
    except Exception as e:
        print(f"{'blender':10} {e}")
    print(f"{'key':10} {'OPENROUTER_API_KEY set' if os.environ.get('OPENROUTER_API_KEY') else 'not set (only needed for --model)'}")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="eyeproof", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def browser_opts(p):
        p.add_argument("--gpu", choices=["soft", "hw"], default="soft",
                       help="soft = SwiftShader on the CPU (default, never touches the GPU); hw = real GPU via Vulkan "
                            "(WebGL + WebGPU, fast for heavy 3D)")
        p.add_argument("--root", help="folder to serve local files from (default: the file's folder)")
        p.add_argument("--wait", type=int, default=500, help="ms to wait after load")
        p.add_argument("--dark", action="store_true", help="prefers-color-scheme: dark")

    def capture_opts(p):
        p.add_argument("targets", nargs="+", help="URL, .html, image, video, frame folder/glob or .blend")
        p.add_argument("-o", "--out")
        p.add_argument("--viewport", nargs="+", default=["desktop", "mobile"], help="desktop laptop hd tablet mobile WxH")
        p.add_argument("--full", action="store_true", help="full page (tiled when tall)")
        p.add_argument("--click", help="CSS selector to click before the shot")
        p.add_argument("--frames", type=int, default=12, help="frames in a video / sequence sheet")
        p.add_argument("--video", action="store_true", help="also send the raw video (models with video input)")
        p.add_argument("--json", action="store_true")
        browser_opts(p)

    def model_opts(p, default=None):
        p.add_argument("--model", default=default, help="OpenRouter vision model for a review (e.g. elorian/glimpse)")
        p.add_argument("--intent", help="what it is supposed to be/do")
        p.add_argument("--ask", help="a specific question")

    p = sub.add_parser("shot", help="screenshots + measured checks, no model (pages, images, videos, frames, .blend)")
    capture_opts(p)
    p.set_defaults(fn=cmd_shot)

    p = sub.add_parser("review", help="shot + measured checks + a vision model's critique")
    capture_opts(p)
    model_opts(p, lk.DEFAULT_MODEL)
    p.set_defaults(fn=cmd_review)

    p = sub.add_parser("play", help="drive a page/game headless through steps, screenshot and measure",
                       description=web.STEP_HELP, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("target", help="URL or local .html (served over http://127.0.0.1); ?query allowed")
    p.add_argument("steps", nargs="*")
    p.add_argument("--steps-file", help="one step per line (# comments)")
    p.add_argument("--viewport", default="laptop")
    p.add_argument("--hook", default="__game", help="window property exposed as g in steps (default __game)")
    p.add_argument("--record", action="store_true", help="record a video of the whole run (+ video checks, sheet)")
    p.add_argument("--frames", type=int, default=12)
    p.add_argument("-o", "--out")
    p.add_argument("--json", action="store_true")
    browser_opts(p)
    p.set_defaults(fn=cmd_play, wait=1000)
    model_opts(p)

    p = sub.add_parser("frames", help="render output / image sequence: pixel checks per frame, frozen/jumps, sheet")
    p.add_argument("targets", nargs="+", help="folder(s), glob(s) or files")
    p.add_argument("--frames", type=int, default=16, help="frames on the sheet (bad frames are added)")
    p.add_argument("-o", "--out")
    model_opts(p)
    p.set_defaults(fn=cmd_frames)

    p = sub.add_parser("blend", help="headless Blender: scene checks + render chosen frames + pixel checks")
    p.add_argument("file", nargs="?", help=".blend file (omit with --python that builds the scene)")
    p.add_argument("--frames", type=int, nargs="+", help="frames to render (default: current frame)")
    p.add_argument("--scale", type=int, default=50, help="resolution percent (default 50)")
    p.add_argument("--samples", type=int, default=8, help="render samples (default 8)")
    p.add_argument("--engine", choices=["eevee", "cycles", "workbench"])
    p.add_argument("--camera")
    p.add_argument("--python", help="script that builds/changes the scene before the check")
    p.add_argument("--no-render", action="store_true", help="scene checks and framing only")
    p.add_argument("-o", "--out", help="output folder (the Blender flatpak cannot write to /tmp)")
    model_opts(p)
    p.set_defaults(fn=cmd_blend)

    p = sub.add_parser("diff", help="before/after: side by side + changed pixels marked")
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("-o", "--out")
    p.set_defaults(fn=cmd_diff)

    p = sub.add_parser("look", help="ask the model about existing image/video files")
    p.add_argument("files", nargs="+")
    p.add_argument("--intent")
    p.add_argument("--ask")
    p.add_argument("--model", default=lk.DEFAULT_MODEL)
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_look)

    p = sub.add_parser("sheet", help="contact sheet of a video, frames stamped with time, spike frames added")
    p.add_argument("video")
    p.add_argument("-o", "--out")
    p.add_argument("--frames", type=int, default=12)
    p.add_argument("--no-spikes", action="store_true", help="only evenly spaced frames")
    p.set_defaults(fn=cmd_sheet)

    p = sub.add_parser("screen", help="screenshot of the real screen (only when the user asks you to look at it)")
    p.add_argument("-o", "--out")
    p.set_defaults(fn=cmd_screen)

    p = sub.add_parser("doctor", help="check ffmpeg, Chromium (soft + hw GPU), Blender, key")
    p.set_defaults(fn=cmd_doctor)

    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except Exception as e:
        print(f"eyeproof {args.cmd}: error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
