# #54 Screenshot per step

- Issue: https://github.com/galipdg/AYNA/issues/54
- Owner: hasan · Branch: `hasan/54-screenshot-per-step`
- Started: 2026-11-15 · Last update: 2026-11-15

## Approach

FR-19 (`docs/rs/RS.md`): after each step, a PNG of the AUT's window, cropped to that window,
returned with the step result. NFR-03 caps the cost at **300 ms per step**.

Most of the design is already settled by other issues' notes, and this note exists so none of it
is re-derived:

- **The crop rectangle is `recognition/uia.py:_frame_bounds(handle)`**, DWM's extended frame
  bounds -- *not* `GetWindowRect` (invisible resize border since Windows 10: 8 px of nothing on
  three sides, measured at 150 %) and not UIA's `BoundingRectangle` (38 px short, no title bar).
  That function already exists and is already the Spy's answer after #184.
- **The coordinate space is physical pixels in virtual-desktop coordinates**, because the agent
  sets per-monitor-v2 DPI awareness (`uia.py:73` says the crop rectangle assumes this). So the
  screenshot and a candidate's `bounds` are in one space and `dpi` never rescales for drawing
  (`docs/agent-rpc.md:400`).
- **`screenshotAt` is this issue's field to name and settle** (`docs/agent-rpc.md:400`), and the
  snapshot's `startedAt` is time-zone aware *because* a screenshot is compared with it
  (`recognition/snapshot.py:143`). A run on the healing path takes the image immediately before
  the snapshot walk, not "at the same moment": a walk can take minutes.
- **The server side is already specified** and is not this issue's work: omer's ADR
  `2026-11-08-run-screenshots-and-retention`, `PUT /api/runs/{runId}/results/{stepIndex}/screenshot`
  with the raw PNG, at most 8 MB, only *after* the step result was accepted. #51 owns it.
- **How the PNG travels agent -> client is this issue's to decide** (`docs/agent-rpc.md:400`:
  "the image itself travels as #54 and #51 decide").

### Branching

Branched from `main`, **not** stacked on `hasan/40-playback-v1`, even though the issue depends on
#40. The capture itself (window -> cropped PNG, under 300 ms, DPI-correct) is independent of the
runner's shape, so it goes in a module of its own and the runner hook is a few lines. #239 is the
reason: #46 was squash-merged and every file its stacked child touched conflicted. Whichever of
#40 / #54 merges second reconciles the `runner.py` hook, which is a far smaller surface than a
stacked branch.

## Decisions (small, local to this task)
- 2026-11-15 — branch from `main` rather than stack on #40 — reason above.
- 2026-11-15 — **the PNG travels as a path, not as base64** (with the user) — a 50-step run is
  ~15 MB of PNG and base64 adds a third, through the same socket as the live status; the agent
  and the client always share a machine, because the client spawns the agent. The result carries
  `screenshotPath` and `screenshotAt`; the client reads the file and PUTs the bytes under #51's
  contract. This also keeps `schemas/agent-rpc.schema.json` out of it for now (see Open issues).
- 2026-11-15 — **no Pillow; the PNG encoder is ours** (with the user) — `pywin32` is already here
  through pywinauto and does the capture, so `zlib` + `struct` writes the file and the agent's
  dependency list stays where #52 froze it. The encoder is a pure function, so it is tested on
  any OS: 8-bit truecolour, filter 0, no interlacing.
- 2026-11-15 — **zlib level 1, not the default 6** — measured below; compression is the only
  part that grows with the window.
- 2026-11-15 — **`PrintWindow` with `PW_RENDERFULLCONTENT`, `BitBlt` only as a fallback** — a
  `BitBlt` of the screen photographs whatever overlaps the app, which is the wrong evidence. The
  result records which one answered (`captured_with`).
- 2026-11-15 — **`frame_bounds` moved to `recognition/frames.py`** — see Open issues: importing
  it from `recognition/uia.py` made the capture need `websockets`, which it does not.
- 2026-11-15 — **a `notRun` step is not photographed, and a failed capture does not fail the
  step** — a step that never ran has no screen, and the commonest reason a step fails is that
  the window is not what the test expected, including gone. Documented in `docs/agent-rpc.md`
  so #59's report treats a missing image as normal.

## Status
- [x] Branch, task note, prior constraints gathered
- [x] Both open questions settled with the user (path transport, stdlib encoder)
- [x] `playback/screenshot.py`: encoder, BGRA->RGB, crop, capture, `step_capture`, run directory
- [x] `recognition/frames.py`: `window_rect` + `frame_bounds`, free of UIA and RPC
- [x] Hook in `run_steps` / `StepResult` (`screenshotPath`, `screenshotAt`), and in
      `UiaDesktop.run_steps` so the RPC path gets it without touching galip's `rpc.py`
- [x] Tests: 25 pure (`tests/test_screenshot.py`) + 8 Windows (`tests/test_screenshot_windows.py`)
      + 6 runner-hook tests. **475 agent tests green on 2026-11-15**, ruff clean.
- [x] `docs/agent-rpc.md`: the two fields, the coordinate space, and that absent is normal
- [x] NFR-03 measured (below)
- [ ] Acceptance criteria ticked on the issue, PR opened
- Next step: open the PR (`Closes #54`) with both reviews requested, and say in the body that
  the client side (reading the file and uploading it) is #51's and omer's, not this PR's.

## Measurements (2026-11-15, this Windows machine)
- **A real window, end to end** (`capture_window_png`, including crop and encode): **41 ms** for
  the sample app at 902x564, **91-96 ms** for a 1920x1020 window. NFR-03 allows 300 ms, so the
  criterion is met with room.
- **The encoder alone, 1920x1080**: 29 ms / 30 KiB for a frame shaped like an app window;
  226-295 ms / 6 MB for random noise. So the budget is comfortable for the windows AYNA tests
  and has **no margin for genuinely incompressible content** (a photo, a video surface). Kept as
  a measurement in `test_an_incompressible_frame_is_the_one_case_with_no_budget_left`, whose
  assertion is deliberately loose; see Open issues.
- **The image was looked at, not only measured**: the sample app's `main` screen captured to a
  PNG and opened -- upright, true colours, title bar included, cropped exactly to the visible
  frame with no desktop border down the sides.

## Manual checks
- 2026-11-15 · hasan · capture the sample app's `main` window and open the PNG · **pass** ·
  evidence: 902x564 via `printWindow` in 41 ms, 21 KiB; the image is the window. Not committed
  (generated output).
- Still owed at a Windows session: **a second display at a different scaling**. Everything here
  was measured at 125 % on one monitor, and the crop is where a DPI mistake would show.

## Open issues
- **Nothing deletes the PNGs.** The agent writes one directory per run under the system
  temporary directory and cannot know when the client has finished uploading them, so cleanup
  belongs to whoever owns the run. Said so in `docs/agent-rpc.md` and in omer's inbox (#51/#59);
  the client already removes report files for the same reason.
- **`screenshotPath` and `screenshotAt` are not in `schemas/agent-rpc.schema.json`.** omer's #52
  note says added optional fields are a minor bump (`$defs/version`), but `schemas/` is shared
  and frozen at v1, so this PR documents the fields and leaves the schema to the review. The
  `contracts` CI job will say whether it minds.
- **NFR-03 has no margin for an incompressible window.** Not a problem for any AYNA pilot app,
  but if it ever is, the lever is the image, not the encoder: capture at a reduced size or drop
  to a palette. Worth an issue only if a real app hits it.
- **The `websockets` coupling is now gone, and this PR finished it off.** Two separate things
  happened: `recognition/frames.py` took the two rectangles out of `recognition/uia.py` so a
  capture needs no UIA backend at all; and, after merging `origin/main`, galip's
  `agent/ayna_agent/errors.py` turned out to be on `main` (#40/#244) **while `uia.py` was still
  importing those four exceptions from `ayna_agent.rpc`** -- so the decoupling it was written for
  had not actually taken effect. One line in `uia.py` (my file) now points at
  `ayna_agent.errors`, and `import ayna_agent.recognition.uia` works on the repo-root `.venv`
  for the first time. **#29's `capture` no longer needs `agent/.venv`**; that note in
  `active.md` and `learnings.md` is now out of date.

## Handoff
- **The capture is on by default for every `runSteps` call** (`UiaDesktop.run_steps`), which is
  what FR-19 asks for. A caller that does not want it passes its own directory; the runner's
  `capture` parameter is optional and `run_steps` without one behaves exactly as #26 did, so
  nothing that existed before this issue changed shape.
- **`test_the_capture_is_top_down_and_not_bottom_up` is the test to keep, and its first version
  was wrong in a way worth remembering.** A DIB is bottom-up unless its height is negative, and
  nothing else in the suite would notice if that flipped: the PNG would still be a valid PNG of
  the right size. The first version compared our top row with `GetPixel` at the window's
  top-left corner **on screen**, which passed here and **failed on the CI runner** -- correctly:
  `PrintWindow` draws the *window* and `GetPixel` reads the *screen*, and they differ wherever
  another window overlaps or, on Windows 11, where a rounded corner leaves that pixel undrawn in
  the capture (CI saw black against the desktop's blue). It now reads the same window twice
  top-down and once bottom-up: the two readings must be each other's reverse, which is a fact
  about `_dib_bits` whatever the window shows, and the repeat makes a repainting window skip
  instead of fail.
- The `eval` and `agent` suites both showed an intermittent UIA readiness flake today, in tests
  that do not touch this work (`eval/apps/sample/tests/test_sample_uia.py` and
  `agent/tests/test_playback_trial_app.py`). It is #69 data and is written up in the #47 task
  note and `learnings.md`; do not mistake it for a screenshot problem.

## Outcome (fill when the issue closes)
