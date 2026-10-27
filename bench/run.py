"""Benchmark: which eyes find the planted defects? Glimpse (OpenRouter) vs Claude (headless claude -p).

Modes: raw  = pixels only (screenshots / an evenly spaced video sheet)
       tool = the full eyeproof pipeline (measured facts in the prompt, motion-spike frames in the sheet)
Usage: OPENROUTER_API_KEY=... .venv/bin/python bench/run.py [--only glimpse,opus] [--modes raw,tool] [--fixtures ...]
Claude contestants need Claude Code (`claude -p`); the Blender fixtures need Blender.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from eyeproof import capture, look as lk

HERE = Path(__file__).resolve().parent
CONTESTANTS = {
    "glimpse": {"kind": "openrouter", "model": "elorian/glimpse"},
    "opus": {"kind": "claude", "model": "opus"},
    "sonnet": {"kind": "claude", "model": "sonnet"},
}


def prepare(fx: dict, mode: str, out: Path) -> tuple[list[str], list[str], str | None]:
    """Files every contestant sees, the measured facts (tool mode), and a raw video only video models get."""
    src = HERE / fx["file"]
    d = out / "inputs" / mode / fx["id"]
    if fx["viewport"] == "video":
        sheet = capture.sheet(src, d / "sheet.png", n=12, spikes=mode == "tool")
        facts = []
        if mode == "tool":
            m = capture.motion(src)
            facts = [f"[video] motion spike at t={s['t']}s (change {s['change']} vs median {m['median_change']})"
                     for s in m["spikes"]]
        return [str(sheet)], facts, str(src)
    if fx["viewport"] == "blend":
        from eyeproof import blend
        rep = blend.blend(str(src), d, frames=[1], scale=75, samples=16)
        facts = rep["all_facts"] + [e["summary"] for e in rep["frames"].values()] if mode == "tool" else []
        return rep["files"], facts, None
    rep = capture.shot(str(src), d, viewports=[fx["viewport"]], full=False, wait_ms=300, checks=mode == "tool")
    files = [f for s in rep["shots"].values() for f in s["files"]]
    return files, capture.findings(rep) if mode == "tool" else [], None


def ask_claude(model: str, files: list[str], prompt: str) -> dict:
    listing = "\n".join(f"- {f}" for f in files)
    full = f"{prompt}\n\nThe material is in these image files. Read every one of them before answering:\n{listing}"
    t0 = time.time()
    r = subprocess.run(["claude", "-p", "--model", model, "--output-format", "json", "--tools", "Read",
                        "--allowedTools", "Read", "--no-session-persistence", "--strict-mcp-config",
                        "--disable-slash-commands", full],
                       capture_output=True, text=True, timeout=600, cwd=HERE)
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"model": model, "text": r.stdout[-2000:] + r.stderr[-1000:], "result": None,
                "seconds": round(time.time() - t0, 1), "cost_usd": None, "error": True}
    text = data.get("result", "")
    return {"model": model, "text": text, "result": lk.parse_json(text), "seconds": round(time.time() - t0, 1),
            "cost_usd": data.get("total_cost_usd")}


def issue_text(i: dict) -> str:
    return f"{i.get('where', '')} {i.get('what', '')}".lower()


def score(fx: dict, res: dict) -> dict:
    issues = (res.get("result") or {}).get("issues") or []
    found, used = {}, set()
    for d in fx["defects"]:
        hit = next((k for k, i in enumerate(issues)
                    if any(all(re.search(g, issue_text(i)) for g in alt) for alt in d["any"])), None)
        found[d["id"]] = hit is not None
        if hit is not None:
            used.add(hit)
    extra = [i for k, i in enumerate(issues) if k not in used]
    return {"found": found, "n_found": sum(found.values()), "n_defects": len(fx["defects"]),
            "extra": len(extra), "extra_major": sum(i.get("severity") in ("blocker", "major") for i in extra),
            "parsed": res.get("result") is not None}


def run_one(name: str, fx: dict, mode: str, files: list[str], facts: list[str], video: str | None, out: Path) -> dict:
    c = CONTESTANTS[name]
    prompt = lk.build_prompt(fx["intent"], None, "\n".join(facts) or None)
    try:
        if c["kind"] == "openrouter":
            res = lk.look(files + ([video] if video else []), prompt, model=c["model"])
        else:
            res = ask_claude(c["model"], files, prompt)
    except Exception as e:
        res = {"model": c["model"], "text": str(e), "result": None, "seconds": None, "cost_usd": None, "error": True}
    row = {"contestant": name, "fixture": fx["id"], "mode": mode, **score(fx, res),
           "seconds": res.get("seconds"), "cost_usd": res.get("cost_usd")}
    (out / "raw").mkdir(parents=True, exist_ok=True)
    (out / "raw" / f"{name}-{mode}-{fx['id']}.json").write_text(json.dumps({**row, "reply": res}, indent=2))
    print(f"{name:8} {mode:4} {fx['id']:18} {row['n_found']}/{row['n_defects']} extra={row['extra']}"
          f" {row['seconds']}s ${row['cost_usd'] or 0:.4f}", flush=True)
    return row


def summarize(rows: list[dict]) -> str:
    lines = ["| contestant | mode | defects found | recall | false alarms on clean pages | extra issues on buggy pages | cost | avg s |",
             "|---|---|---|---|---|---|---|---|"]
    for name in CONTESTANTS:
        for mode in ("raw", "tool"):
            rs = [r for r in rows if r["contestant"] == name and r["mode"] == mode]
            if not rs:
                continue
            f, n = sum(r["n_found"] for r in rs), sum(r["n_defects"] for r in rs)
            clean = sum(r["extra"] for r in rs if r["n_defects"] == 0)
            extra = sum(r["extra"] for r in rs if r["n_defects"])
            cost = sum(r["cost_usd"] or 0 for r in rs)
            secs = [r["seconds"] for r in rs if r["seconds"]]
            lines.append(f"| {name} | {mode} | {f}/{n} | {f / n:.0%} | {clean} | {extra} | ${cost:.3f} |"
                         f" {sum(secs) / max(len(secs), 1):.0f} |")
    defects = sorted({(r["fixture"], d) for r in rows for d in r["found"]})
    combos = [(c, m) for c in CONTESTANTS for m in ("raw", "tool") if any(r["contestant"] == c and r["mode"] == m for r in rows)]
    lines += ["", "| defect | " + " | ".join(f"{c} {m}" for c, m in combos) + " |", "|---|" + "---|" * len(combos)]
    for fxid, d in defects:
        cells = []
        for c, m in combos:
            r = next((r for r in rows if r["contestant"] == c and r["mode"] == m and r["fixture"] == fxid), None)
            cells.append("✓" if r and r["found"].get(d) else "·")
        lines.append(f"| {fxid}/{d} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def rescore(out: Path) -> None:
    truth = {f["id"]: f for f in json.loads((HERE / "truth.json").read_text())}
    rows = []
    for f in sorted((out / "raw").glob("*.json")):
        d = json.loads(f.read_text())
        r = d["reply"]
        rows.append({**{k: d[k] for k in ("contestant", "fixture", "mode")}, **score(truth[d["fixture"]], r),
                     "seconds": r.get("seconds"), "cost_usd": r.get("cost_usd")})
    (out / "rows.json").write_text(json.dumps(rows, indent=2))
    table = summarize(rows)
    (out / "summary.md").write_text(table + "\n")
    print(table)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=",".join(CONTESTANTS))
    ap.add_argument("--modes", default="raw,tool")
    ap.add_argument("--fixtures", default="")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--out", default=str(HERE / "runs" / time.strftime("%Y%m%d-%H%M%S")))
    ap.add_argument("--rescore", help="re-score the raw replies of an earlier run dir (after truth.json changed)")
    a = ap.parse_args()
    if a.rescore:
        rescore(Path(a.rescore))
        return
    out = Path(a.out)
    fixtures = [f for f in json.loads((HERE / "truth.json").read_text())
                if not a.fixtures or f["id"] in a.fixtures.split(",")]
    jobs = []
    for mode in a.modes.split(","):
        for fx in fixtures:
            files, facts, video = prepare(fx, mode, out)
            jobs += [(n, fx, mode, files, facts, video) for n in a.only.split(",")]
    with ThreadPoolExecutor(a.jobs) as ex:
        rows = list(ex.map(lambda j: run_one(*j, out), jobs))
    (out / "rows.json").write_text(json.dumps(rows, indent=2))
    table = summarize(rows)
    (out / "summary.md").write_text(table + "\n")
    print("\n" + table + f"\n\n→ {out}")


if __name__ == "__main__":
    main()
