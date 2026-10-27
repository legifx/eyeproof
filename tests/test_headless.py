"""Headless features: pixel checks, sequences, games (play/record), video facts, Blender."""
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from eyeproof import pixels, video, web

FX = Path(__file__).resolve().parent.parent / "bench" / "fixtures"
GAME = str(FX / "game" / "index.html")


def scene(path: Path, x: int = 40, colour=(200, 60, 60)) -> Path:
    im = Image.new("RGB", (320, 180), (90, 140, 210))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 130, 320, 180), fill=(60, 140, 60))
    d.rectangle((x, 90, x + 40, 130), fill=colour)
    im.save(path)
    return path


def test_pixels_blank_black_and_magenta(tmp_path):
    Image.new("RGB", (64, 64), (0, 0, 0)).save(tmp_path / "black.png")
    assert any("blank" in f and "black" in f for f in pixels.check(tmp_path / "black.png"))
    scene(tmp_path / "ok.png")
    assert pixels.check(tmp_path / "ok.png") == []
    scene(tmp_path / "pink.png", colour=(190, 70, 190))  # shaded magenta, not pure (255, 0, 255)
    assert any("magenta" in f for f in pixels.check(tmp_path / "pink.png"))


def test_sequence_finds_frozen_run_and_bad_frame(tmp_path):
    frames = [scene(tmp_path / f"f_{i:03d}.png", x=20 + 10 * min(i, 4)) for i in range(10)]  # moves, then stops
    Image.new("RGB", (320, 180), (0, 0, 0)).save(frames[8])
    rep = video.frames_report(video.collect([str(tmp_path / "f_*.png")]), tmp_path / "out", n=6)
    text = "\n".join(rep["facts"])
    assert "identical frames" in text and "f_008.png is blank" in text
    assert Path(rep["sheet"]).exists()


def test_diff_marks_change(tmp_path):
    r = pixels.diff_image(scene(tmp_path / "a.png"), scene(tmp_path / "b.png", x=200), tmp_path / "d.png")
    assert 0.01 < r["changed"] < 0.2 and r["bbox"]


def test_video_facts_spikes(tmp_path):
    text = "\n".join(video.facts(FX / "09-anim.mp4"))
    assert "t=3.0s" in text and "t=4.5s" in text and "no audio" in text


def test_play_game_detects_ignored_input_and_freeze(tmp_path):
    ok = web.play(GAME, ["until:g.ready", "key:ArrowRight:600", "expect:g.player.x > 120", "burst:idle:3:250"],
                  tmp_path / "ok")
    assert ok["facts"] == [] and "SwiftShader" in ok["gfx"]["webgl"]
    deaf = web.play(GAME + "?bug=deaf", ["until:g.ready", "key:ArrowRight:600", "expect:g.player.x > 120"],
                    tmp_path / "deaf")
    assert any("expect failed" in f for f in deaf["facts"])
    frozen = web.play(GAME + "?bug=freeze", ["until:g.ready", "wait:1500", "burst:idle:3:250"], tmp_path / "frz")
    assert any("not animating" in f for f in frozen["facts"])


def test_play_records_video(tmp_path):
    rep = web.play(GAME, ["until:g.ready", "key:ArrowRight:800"], tmp_path, record=True)
    assert Path(rep["video"]).exists() and video.probe(Path(rep["video"]))["duration"] > 0.5


@pytest.mark.skipif(not (shutil.which("blender") or (shutil.which("flatpak") and subprocess.run(
    ["flatpak", "info", "org.blender.Blender"], capture_output=True).returncode == 0)), reason="no Blender")
def test_blend_scene_checks_and_render():
    from eyeproof import blend
    out = Path(__file__).resolve().parent.parent / ".eyeproof" / "test-blend"  # flatpak cannot see /tmp
    rep = blend.blend(str(FX / "scene.blend"), out, frames=[1], scale=25, samples=4)
    text = "\n".join(rep["all_facts"])
    assert "missing image file" in text and "without material" in text and "magenta" in text
    assert "Pillar" in rep["frames"]["1"]["summary"] and "cut right" in rep["frames"]["1"]["summary"]
