from pathlib import Path

from eyeproof import capture, look

FX = Path(__file__).resolve().parent.parent / "bench" / "fixtures"


def test_page_checks_fire_on_planted_defects(tmp_path):
    rep = capture.shot(str(FX / "02-pricing.html"), tmp_path, viewports=["desktop"])
    lines = "\n".join(capture.findings(rep))
    assert "NaN" in lines and "overlaps" in lines
    assert Path(rep["shots"]["desktop"]["files"][0]).exists()


def test_mobile_overflow_uses_configured_viewport(tmp_path):
    lines = "\n".join(capture.findings(capture.shot(str(FX / "04-mobile.html"), tmp_path, viewports=["mobile"])))
    assert "horizontal scroll" in lines and "Settings" in lines


def test_clean_page_is_quiet(tmp_path):
    rep = capture.shot(str(FX / "07-clean-article.html"), tmp_path, viewports=["desktop"])
    assert capture.findings(rep) == []


def test_motion_spikes_find_both_glitches(tmp_path):
    video = FX / "09-anim.mp4"
    times = [s["t"] for s in capture.motion(video)["spikes"]]
    assert 3.0 in times and 4.5 in times
    assert capture.sheet(video, tmp_path / "s.png", n=8).exists()


def test_parse_json_tolerates_fences():
    assert look.parse_json('ok:\n```json\n{"verdict": "ok", "issues": []}\n```')["verdict"] == "ok"
    assert look.parse_json("no json here") is None
