"""Headless browser: pages, canvas/WebGL/WebGPU games, scripted play, recording.

Local files are served over http://127.0.0.1 (never file://): WebGPU needs a secure context and ES modules,
fetch() and workers break under file://.
"""
from __future__ import annotations

import contextlib
import functools
import http.server
import json
import re
import socketserver
import threading
import time
from pathlib import Path

from . import pixels

VIEWPORTS = {"desktop": (1440, 900), "laptop": (1280, 800), "hd": (1920, 1080), "tablet": (834, 1112),
             "mobile": (390, 844)}

# soft: SwiftShader (CPU) for WebGL + WebGPU; never touches the GPU (safe while games or local LLMs use it)
# hw:   the real GPU through Vulkan for WebGL and WebGPU; fast and faithful for heavy 3D
GPU_ARGS = {
    "soft": ["--enable-unsafe-swiftshader", "--enable-unsafe-webgpu", "--autoplay-policy=no-user-gesture-required"],
    "hw": ["--enable-unsafe-webgpu", "--ignore-gpu-blocklist", "--use-angle=vulkan",
           "--enable-features=Vulkan,WebGPU,VulkanFromANGLE,DefaultANGLEVulkan",
           "--autoplay-policy=no-user-gesture-required"],
}

DOM_CHECKS = r"""
([vw, vh]) => {
  // vw/vh come from the configured viewport: on mobile innerWidth grows with overflowing content
  const out = {};
  const label = el => {
    const t = (el.innerText || el.alt || el.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ');
    let s = el.tagName.toLowerCase();
    if (el.id) s += '#' + el.id;
    else if (el.classList.length) s += '.' + [...el.classList].slice(0, 2).join('.');
    return t ? `${s} "${t.slice(0, 50)}"` : s;
  };
  const visible = el => { const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && +cs.opacity > 0.05; };
  const all = [...document.querySelectorAll('body *')].filter(visible).slice(0, 4000);
  const leaves = all.filter(el => [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()));

  out.page_scroll_width = document.documentElement.scrollWidth;
  out.horizontal_scroll = document.documentElement.scrollWidth > vw + 1;
  out.off_right = all.filter(el => { const r = el.getBoundingClientRect(); return r.right > vw + 2 && r.left < vw; })
    .filter(el => !(el.parentElement && el.parentElement.getBoundingClientRect().right > vw + 2))  // outermost only
    .slice(0, 8).map(el => `${label(el)} right=${Math.round(el.getBoundingClientRect().right)}px > ${vw}px`);
  out.fixed_cut_off = all.filter(el => ['fixed', 'sticky'].includes(getComputedStyle(el).position))
    .filter(el => { const r = el.getBoundingClientRect(); return r.bottom > vh + 2 && r.top < vh; })
    .slice(0, 4).map(el => `${label(el)} bottom=${Math.round(el.getBoundingClientRect().bottom)}px > ${vh}px (fixed, cannot be scrolled into view)`);
  out.text_overflow = leaves.filter(el => el.scrollWidth > el.clientWidth + 2 && el.clientWidth > 0 &&
      getComputedStyle(el).display !== 'inline')
    .slice(0, 8).map(el => `${label(el)} content ${el.scrollWidth}px in box ${el.clientWidth}px`);
  out.broken_images = [...document.images].filter(i => i.complete && i.naturalWidth === 0)
    .map(i => `img src="${(i.getAttribute('src') || '').slice(0, 80)}" alt="${i.alt}"`);

  const rgb = s => (s.match(/[\d.]+/g) || []).map(Number);
  const lum = ([r, g, b]) => { const f = c => (c /= 255) <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const bgOf = el => { for (let e = el; e; e = e.parentElement) { const cs = getComputedStyle(e);
      if (cs.backgroundImage !== 'none') return null; const c = rgb(cs.backgroundColor);
      if (c.length >= 3 && (c.length < 4 || c[3] > 0.5)) return c; } return [255, 255, 255]; };
  out.low_contrast = leaves.map(el => { const bg = bgOf(el); if (!bg) return null;
      const fg = rgb(getComputedStyle(el).color); const a = lum(fg), b = lum(bg);
      const ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
      return ratio < 3 ? `${label(el)} contrast ${ratio.toFixed(2)}:1` : null; })
    .filter(Boolean).slice(0, 8);

  const rects = leaves.slice(0, 400).map(el => [el, el.getBoundingClientRect()]);
  const ov = [];
  for (let i = 0; i < rects.length && ov.length < 8; i++) for (let j = i + 1; j < rects.length && ov.length < 8; j++) {
    const [a, ra] = rects[i], [b, rb] = rects[j];
    if (a.contains(b) || b.contains(a)) continue;
    const w = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left), h = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
    if (w > 4 && h > 4 && w * h > 0.25 * Math.min(ra.width * ra.height, rb.width * rb.height)) ov.push(`${label(a)} overlaps ${label(b)}`);
  }
  out.text_overlap = ov;
  const body = document.body.innerText || '';
  out.placeholder_text = [...new Set((body.match(/lorem ipsum|\bTODO\b|\bundefined\b|\bNaN\b|\[object Object\]|\{\{.*?\}\}/gi) || []))];
  out.canvases = [...document.querySelectorAll('canvas')].filter(visible).slice(0, 6).map(c => {
    const r = c.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    return {label: label(c), rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)],
      w: c.width, h: c.height, dpr, blurry: c.width < r.width * dpr * 0.75 || c.height < r.height * dpr * 0.75}; });
  return out;
}
"""

GFX_INFO = r"""
async () => {
  const c = document.createElement('canvas'), gl = c.getContext('webgl2') || c.getContext('webgl');
  let webgl = 'unavailable';
  if (gl) { const e = gl.getExtension('WEBGL_debug_renderer_info');
    webgl = e ? gl.getParameter(e.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER); }
  let webgpu = navigator.gpu ? 'no adapter' : (isSecureContext ? 'unavailable' : 'unavailable (not a secure context)');
  try { const a = navigator.gpu && await navigator.gpu.requestAdapter();
    if (a) webgpu = [a.info?.vendor, a.info?.architecture].filter(Boolean).join(' ') || 'adapter'; } catch (e) {}
  return {webgl, webgpu};
}
"""

FPS_JS = r"""
(ms) => new Promise(res => { let n = 0; const t0 = performance.now();
  const tick = () => { n++; if (performance.now() - t0 < ms) requestAnimationFrame(tick);
    else res(Math.round(n * 1000 / (performance.now() - t0))); };
  requestAnimationFrame(tick); })
"""


# warnings our own screenshots cause (reading back the WebGL buffer), not the page's fault
SELF_NOISE = re.compile(r"GPU stall due to ReadPixels|GL Driver Message \(OpenGL, Performance")


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def end_headers(self):
        # cross-origin isolation lets games use SharedArrayBuffer / high-res timers like in production
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


@contextlib.contextmanager
def serve(target: str, root: str | None = None):
    """Yield an http URL for target: URLs pass through, local files are served from their folder (or root)."""
    if "://" in target:
        yield target
        return
    path, q, query = target.partition("?")
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(path)
    base = Path(root).expanduser().resolve() if root else (p if p.is_dir() else p.parent)
    rel = "" if p == base else p.relative_to(base).as_posix()
    handler = functools.partial(_Quiet, directory=str(base))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler) as httpd:
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            yield f"http://127.0.0.1:{httpd.server_address[1]}/{rel}{q}{query}"
        finally:
            httpd.shutdown()


def parse_viewport(v: str) -> tuple[str, tuple[int, int]]:
    if v in VIEWPORTS:
        return v, VIEWPORTS[v]
    w, h = v.lower().split("x")
    return v, (int(w), int(h))


class Session:
    """One browser page with everything it says recorded (console, page errors, failed requests)."""

    def __init__(self, browser, viewport: str, dark=False, video_dir: Path | None = None):
        self.name, (self.w, self.h) = parse_viewport(viewport)
        mobile = self.name == "mobile"
        opts = dict(viewport={"width": self.w, "height": self.h}, color_scheme="dark" if dark else "light",
                    is_mobile=mobile, has_touch=mobile)
        if video_dir:
            opts.update(record_video_dir=str(video_dir), record_video_size={"width": self.w, "height": self.h})
        self.ctx = browser.new_context(**opts)
        self.page = self.ctx.new_page()
        self.console, self.failed = [], []
        self.page.on("console", lambda m: m.type in ("error", "warning") and not SELF_NOISE.search(m.text)
                     and self.console.append(f"{m.type}: {m.text}"[:300]))
        self.page.on("pageerror", lambda e: self.console.append(f"pageerror: {e}"[:300]))
        self.page.on("response", lambda r: r.status >= 400 and self.failed.append(f"{r.status} {r.url}"[:200]))
        self.page.on("requestfailed", lambda r: self.failed.append(f"failed {r.url}"[:200]))

    def goto(self, url: str, wait_ms: int):
        try:
            self.page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception as e:  # still look at whatever loaded
            self.console.append(f"goto: {e}"[:300])
        self.page.wait_for_timeout(wait_ms)

    def checks(self) -> dict:
        return self.page.evaluate(DOM_CHECKS, [self.w, self.h])

    def gfx(self) -> dict:
        return self.page.evaluate(GFX_INFO)

    def fps(self, ms: int = 1000) -> int:
        return self.page.evaluate(FPS_JS, ms)


@contextlib.contextmanager
def browser(gpu: str = "soft"):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(args=GPU_ARGS[gpu])
        try:
            yield b
        finally:
            b.close()


def canvas_facts(png: Path, checks: dict) -> list[str]:
    """Crop each visible canvas out of the screenshot and judge its pixels (blank, black, magenta …)."""
    from PIL import Image
    out = []
    if not checks.get("canvases"):
        return out
    im = Image.open(png)
    for c in checks["canvases"]:
        x, y, w, h = c["rect"]
        box = (max(0, x), max(0, y), min(im.width, x + w), min(im.height, y + h))
        if box[2] - box[0] < 8 or box[3] - box[1] < 8:
            continue
        out += pixels.judge(pixels.stats(im.crop(box)), f"canvas {c['label']}")
        if c.get("blurry"):
            out.append(f"canvas {c['label']} draws {c['w']}x{c['h']} px into a {w}x{h} CSS box at DPR "
                       f"{c['dpr']}: upscaled, looks blurry")
    return out


def dedupe(lines: list[str]) -> list[str]:
    """Same finding in several shots → one line with a count, first-seen order kept."""
    counts: dict[str, int] = {}
    for l in lines:
        counts[l] = counts.get(l, 0) + 1
    return [l if n == 1 else f"{l} (×{n})" for l, n in counts.items()]


def findings(report: dict) -> list[str]:
    """Measured facts that fired, as plain lines."""
    lines = []
    for name, s in report.get("shots", {}).items():
        c = s.get("checks", {})
        if c.get("horizontal_scroll"):
            lines.append(f"[{name}] horizontal scroll: page is {c['page_scroll_width']}px wide, viewport {s['viewport'][0]}px")
        for k, title in (("off_right", "leaves viewport"), ("fixed_cut_off", "cut off at bottom"),
                         ("text_overflow", "text overflows box"), ("broken_images", "broken image"),
                         ("low_contrast", "low contrast"), ("text_overlap", "text overlap"),
                         ("placeholder_text", "placeholder text")):
            for item in c.get(k, []):
                lines.append(f"[{name}] {title}: {item}")
        for item in s.get("pixels", []):
            lines.append(f"[{name}] pixels: {item}")
        for item in s.get("console", []):
            lines.append(f"[{name}] console {item}")
        for item in s.get("failed", []):
            lines.append(f"[{name}] request {item}")
    return lines


def shot(target: str, out: Path, viewports=("desktop", "mobile"), full: bool = False, wait_ms: int = 500,
         dark: bool = False, click: str | None = None, checks: bool = True, gpu: str = "soft",
         root: str | None = None) -> dict:
    """Screenshot a URL or local file per viewport, with console errors, DOM checks and canvas pixel checks."""
    out.mkdir(parents=True, exist_ok=True)
    report = {"target": target, "shots": {}}
    with serve(target, root) as url, browser(gpu) as b:
        report["url"] = url
        for v in viewports:
            s = Session(b, v, dark)
            s.goto(url, wait_ms)
            if click:
                s.page.click(click)
                s.page.wait_for_timeout(300)
            png = out / f"{s.name}.png"
            s.page.screenshot(path=str(png), full_page=full)
            entry = {"viewport": [s.w, s.h], "files": [str(t) for t in pixels.tile(png)], "title": s.page.title()}
            if checks:
                entry["checks"] = s.checks()
                entry["pixels"] = canvas_facts(png, entry["checks"]) if not full else []
            entry.update(console=s.console, failed=s.failed)
            report["shots"][s.name] = entry
            s.ctx.close()
    return report


# ---------------------------------------------------------------- scripted play

STEP_HELP = """steps (one per argument or line):
  wait:MS              wait
  until:EXPR           wait until JS is truthy (g = the game hook object), 30 s timeout
  shot:NAME            screenshot (+ pixel and canvas checks)
  burst:NAME:N:MS      N screenshots MS apart (+ frozen / jump check across them)
  key:KEY[:MS]         hold a key MS ms (default 100), e.g. key:ArrowRight:800, key:w:1500
  press:KEY            tap a key or chord (Space, Enter, Control+s)
  type:TEXT            type text
  click:X,Y | click:SELECTOR
  move:X,Y             move the mouse   drag:X1,Y1,X2,Y2   scroll:DY
  fps[:MS]             measure requestAnimationFrame rate (default 1000 ms)
  log:EXPR             evaluate JS and record the value (e.g. log:g.player.hp)
  expect:EXPR          assert game state, a finding if falsy (e.g. expect:g.player.x > 120); use it to prove input
                       works, a moving scene always "changes" on screen
  anything else        JS run in the page with g = window[hook], awaited"""


def _js(page, expr: str, hook: str):
    return page.evaluate("async ([e, h]) => { const g = window[h]; return await (new Function('g', "
                         "'return (async () => (' + e + '))()'))(g); }", [expr, hook])


def play(target: str, steps: list[str], out: Path, viewport: str = "desktop", wait_ms: int = 1000,
         gpu: str = "soft", hook: str = "__game", record: bool = False, root: str | None = None,
         dark: bool = False) -> dict:
    """Drive a page or game headless through steps; screenshots, pixel checks and whether input changed anything."""
    out.mkdir(parents=True, exist_ok=True)
    log, shots, facts = [], [], []
    vdir = out / "video-raw" if record else None
    with serve(target, root) as url, browser(gpu) as b:
        s = Session(b, viewport, dark, video_dir=vdir)
        s.goto(url, wait_ms)
        report = {"target": target, "url": url, "viewport": [s.w, s.h], "gpu": gpu, "gfx": s.gfx()}
        last_png, inputs_since = None, []

        def take(name: str) -> Path:
            nonlocal last_png, inputs_since
            png = out / f"{len(shots) + 1:02d}-{re.sub(r'[^A-Za-z0-9_.-]', '_', name)}.png"
            s.page.screenshot(path=str(png))
            st = pixels.stats(png)
            chk = s.checks()
            # whole-page pixels: judge strictly only without a canvas (a white web page is not "over-exposed")
            judged = pixels.judge(st, name) if not chk.get("canvases") else []
            entry = {"name": name, "file": str(png), "after": [*inputs_since],
                     "pixels": [j for j in judged if "blank" in j or "magenta" in j or "transparent" in j]}
            entry["pixels"] += canvas_facts(png, chk)
            if last_png is not None:
                entry["change"] = pixels.change(last_png, png)
                if inputs_since and entry["change"] < 0.05:
                    entry["pixels"].append(f"{name}: nothing on screen changed after {', '.join(inputs_since)}")
            shots.append(entry)
            last_png, inputs_since = png, []
            return png

        for raw in steps:
            step = raw.strip()
            if not step or step.startswith("#"):
                continue
            op, _, arg = step.partition(":")
            t0 = time.time()
            try:
                if op == "wait":
                    s.page.wait_for_timeout(int(arg))
                elif op == "until":
                    s.page.wait_for_function("([e, h]) => new Function('g', 'return (' + e + ')')(window[h])",
                                             arg=[arg, hook], timeout=30000)
                elif op == "shot":
                    take(arg or f"shot{len(shots) + 1}")
                elif op == "burst":
                    name, n, ms = (arg.split(":") + ["8", "250"])[:3]
                    frames = []
                    for i in range(int(n)):
                        frames.append(take(f"{name}-{i + 1}"))
                        if i < int(n) - 1:
                            s.page.wait_for_timeout(int(ms))
                    seq = pixels.sequence(frames, [i * int(ms) / 1000 for i in range(int(n))])
                    if seq["all_identical"]:
                        facts.append(f"burst {name}: all {n} frames identical over {(int(n) - 1) * int(ms)} ms: "
                                     f"the scene is not animating (paused, crashed render loop or static)")
                    else:
                        facts += [f"burst {name}: {x}" for x in seq["frozen"]]
                    facts += [f"burst {name}: {x}" for x in seq["spikes"]]
                elif op == "key":
                    key, _, hold = arg.partition(":")
                    s.page.keyboard.down(key)
                    s.page.wait_for_timeout(int(hold or 100))
                    s.page.keyboard.up(key)
                    inputs_since.append(step)
                elif op == "press":
                    s.page.keyboard.press(arg)
                    inputs_since.append(step)
                elif op == "type":
                    s.page.keyboard.type(arg)
                    inputs_since.append(step)
                elif op == "click":
                    if re.fullmatch(r"\s*\d+\s*,\s*\d+\s*", arg):
                        x, y = map(int, arg.split(","))
                        s.page.mouse.click(x, y)
                    else:
                        s.page.click(arg)
                    inputs_since.append(step)
                elif op == "move":
                    x, y = map(int, arg.split(","))
                    s.page.mouse.move(x, y, steps=8)
                    inputs_since.append(step)
                elif op == "drag":
                    x1, y1, x2, y2 = map(int, arg.split(","))
                    s.page.mouse.move(x1, y1)
                    s.page.mouse.down()
                    s.page.mouse.move(x2, y2, steps=12)
                    s.page.mouse.up()
                    inputs_since.append(step)
                elif op == "scroll":
                    s.page.mouse.wheel(0, int(arg))
                    inputs_since.append(step)
                elif op == "fps":
                    fps = s.fps(int(arg or 1000))
                    log.append({"step": step, "value": fps})
                    if fps < 30:
                        facts.append(f"frame rate {fps} fps (requestAnimationFrame{', software GPU' if gpu == 'soft' else ''})")
                    continue
                elif op == "expect":
                    ok = _js(s.page, arg, hook)
                    log.append({"step": step, "value": ok})
                    if not ok:
                        facts.append(f"expect failed: {arg}" + (f" (after {', '.join(inputs_since)})" if inputs_since else ""))
                    continue
                elif op == "log":
                    log.append({"step": step, "value": _js(s.page, arg, hook)})
                    continue
                else:
                    val = _js(s.page, step, hook)
                    inputs_since.append(step[:40])
                    log.append({"step": step, "value": val})
                    continue
                log.append({"step": step, "ms": round((time.time() - t0) * 1000)})
            except Exception as e:
                msg = str(e).splitlines()[0][:240]
                log.append({"step": step, "error": msg})
                facts.append(f"step '{step}' failed: {msg}")
        if not shots:
            take("end")
        video = s.page.video
        s.ctx.close()
        if record and video:
            report["video"] = str(Path(video.path()).rename(out / "recording.webm"))
            with contextlib.suppress(OSError):
                vdir.rmdir()
    report.update(steps=log, shots=shots, console=s.console, failed=s.failed)
    for sh in shots:
        facts += sh["pixels"]
    facts += [f"console {c}" for c in s.console] + [f"request {f}" for f in s.failed]
    report["facts"] = dedupe(facts)
    (out / "play.json").write_text(json.dumps(report, indent=2))
    return report
