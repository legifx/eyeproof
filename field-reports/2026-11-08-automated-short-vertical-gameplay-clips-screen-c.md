# Field report: automated short vertical gameplay clips (screen capture of a game engine, cut with ffmpeg)

- **Project kind:** pipeline that records scripted gameplay headless and cuts it into short vertical videos with labels, sound and an end card
- **Agent / model:** Claude Code, Opus
- **eyeproof version:** 0.2.0
- **Commands used:** shot on video files (about 8 clips, 3 rounds of camera changes)

## What eyeproof caught
- No defect was caught by the measurements alone. Format, length and audio were reported correctly on every clip, which ruled out broken cuts quickly.
- The contact sheet with spike frames made bad camera framing visible at once: a subject hidden behind scenery, and a camera placed outside the playable area. The agent judged this by reading the sheets, not from a measured line.
- Before and after sheets across rounds confirmed that a framing fix worked and that a clip used as a control had not regressed.

## False alarms
- Every clip reported 2 to 4 motion spikes. All were intended: the hard cut between two shots, hit flashes, and a white flash into the end card. Reading the spike frames settled this quickly, but on this kind of edit the lines add little.

## What it missed
- Nothing that it claims to measure. Framing, occlusion and a subject that is too small are outside its checks. They showed up only when looking at the sheets.
- A label changing about two frames after a picture cut was noticed from the sheet by chance, because a spike frame happened to land there. No check covers this kind of sync.

## Friction and bugs in eyeproof
- With many spikes the sheet grows very tall and gets scaled down hard when read back, so small subjects become hard to judge. Frame strips made by hand with ffmpeg were clearer for clips with fewer details to check.
- Spike frames that are almost identical (several frames of the same flash) take up sheet space that even samples could use.

## Ratings (1–5)
| usefulness | accuracy of measurements | speed | ease of use |
|---|---|---|---|
| 4 | 5 | 5 | 5 |

## Suggestions
- An option to limit the sheet size or merge neighbouring spikes into one tile, for example `--max-tiles N`.
- An option to ignore a known time range, such as an intended end card transition, so the remaining spikes stand out.
- An optional check that a given region stays free of change or holds a subject, for clips with fixed safe areas.
