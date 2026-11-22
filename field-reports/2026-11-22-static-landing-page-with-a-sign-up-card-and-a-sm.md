# Field report: static landing page with a sign-up card and a small reveal component (plain HTML, CSS, vanilla JS)

- **Project kind:** A single marketing page built from plain HTML and CSS on top of an existing shared stylesheet and design tokens, with a vanilla JS module that swaps a few states (signed out, joined, a card with an inline SVG illustration). No framework, no canvas.
- **Agent / model:** Claude Code, Fable
- **eyeproof version:** 0.2.0
- **Commands used:** shot (desktop + mobile, with and without --full), play with --steps-file (click, log)

## What eyeproof caught
- Nothing through its measured findings. Three real layout bugs were found by reading the screenshots it made:
  a form marked `hidden` was still visible because a `display:grid` rule overrode the attribute; a large empty band
  above the headline came from an inherited rule that gives every `section` a big top padding; a card state showed the
  wrong tint because a colour variable was inherited from an ancestor.
- `play` with a `log:` step was the fast way to find the padding bug: logging a handful of computed styles and
  bounding boxes in one line pointed straight at the inherited rule.

## False alarms
- "low contrast 1.20:1" on the logo wordmark and on a ghost button, on every run. Both are dark ink on a light page
  and clearly readable in the screenshot. It looks like the check compares the text colour with something other than
  the painted background (the header uses a translucent background with a backdrop filter, the wordmark sits next to
  an inline SVG).
- "low contrast" on a large display headline in the brand accent colour. Technically below 4.5:1, but the text is far
  above the large-text size where 3:1 applies, so it reads as a finding that should be a note.

## What it missed
- A visible element carrying the `hidden` attribute. That is almost always a bug and could be detected cheaply:
  an element with `hidden` whose computed `display` is not `none`.
- Unusually large empty vertical bands inside the first viewport (here about 160 px of nothing between header and
  content).

## Friction and bugs in eyeproof
- The value of a `log:` step is printed after the full expression on the same line. With a long expression the result
  ends up far to the right and is easy to cut off when the output is filtered. Printing the value on its own line, or
  the expression truncated, would help.
- `shot` of a page that depends on a signed-in state cannot show the interesting states. I ended up writing a
  temporary static page with the same markup and styles just to look at them.
- With `--full` the mobile shot is split into parts; the file names differ from the non-full run, which I only noticed
  when the expected file was missing.

## Ratings (1–5)
| usefulness | accuracy of measurements | speed | ease of use |
|---|---|---|---|
| 4 | 2 | 5 | 4 |

## Suggestions
- A check for `[hidden]` elements that are still rendered.
- Contrast: resolve the effective background through translucent layers, and apply the large-text threshold.
- A way to inject state before the shot without a steps file, for example a small script that runs before the first
  screenshot, so pages behind a sign-in can be put into the state worth looking at.
- For `log:` steps print `name → value` with the expression shortened.
