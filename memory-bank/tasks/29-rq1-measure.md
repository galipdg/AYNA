# #29 Recognition measurement harness (RQ1)

- Issue: https://github.com/galipdg/AYNA/issues/29
- Owner: hasan · Branch: `hasan/29-rq1-measure`
- Started: 2026-11-12 · Last update: 2026-11-12

## Approach

Two halves, split exactly where the repo already splits capture from rules:

1. **Capture is Windows-only and does nothing clever.** `measure.py capture <app>` drives the
   agent's own `recognition.UiaDesktop` (`list_windows` + `snapshot`) and writes the resulting
   `urn:ayna:schema:snapshot` document to `eval/rq1/snapshots/<app>/<screen>.json`. The operator
   opens the screens; nothing here tries to navigate a pilot app.
2. **Measurement is pure and runs anywhere.** `measure.py measure` reads those snapshot files and
   writes the CSVs. No UI Automation, so every rule is unit-tested in CI off Windows.

**It measures with the product's own code, not a copy of it.** `measure.py` puts `agent/` on
`sys.path` and imports `ayna_agent.model` and `ayna_agent.playback.resolve` — both are
deliberately UIA-free, so they import on any OS with no new dependency and no CI change. The
alternative was a third copy of the identification rule in `eval/`, which would have made RQ1
measure the harness instead of AYNA.

**What counts as recognised.** SDD §6 says "AYNA identifies the control uniquely from its
descriptor". Made exact here as: build the property set the Spy would propose for the control
(`client/src/shared/repository.ts:98 suggestUses` — the priority's fields in order, a field kept
only when it narrows the match, a generated `automationId` skipped), then count the elements of
the **same window** that match it with `playback.resolve.matches`. Exactly one → recognised.
Scope is the window, because that is the scope the Spy counts in and the scope playback resolves
in.

**What counts as a control.** #6's interactive set (15 control types, `TitleBar` subtrees
excluded), kept identical on purpose so RQ1's numbers sit next to the D1 table in
`eval/spikes/uia-dump.md` and the two can be compared.

Pilots are **HandBrake (P1, WPF)** and **KeePass 2 (P2, WinForms)** per the D1 ADR; KeePassXC is
registered but off by default, as D1 makes it conditional.

## Decisions (small, local to this task)

- 2026-11-12 — **Measure the client's escalating proposal, not `model.primary_property()`** —
  `primary_property()` returns one property name and is used nowhere; `suggestUses` is what a
  tester actually gets when they add an object. Measuring the unused rule would report a number
  no user ever sees. See "Open issues": the two rules disagree and that is worth an issue.
- 2026-11-12 — **Uniqueness is per window, not per app** — the Spy's `matchCount` and playback's
  `resolve` both work inside one window's snapshot. A cross-window number would be a different
  (and much worse) metric that nothing in the product relies on.
- 2026-11-12 — **Two CSVs per app, not one** — `*-rates.csv` carries the per-control-type rates
  the issue asks for; `*-controls.csv` is one row per control and doubles as the sheet a human
  labels for ground truth. The guide's procedure needs the per-control rows; the criterion needs
  the rates.
- 2026-11-12 — **Snapshots are committed and never re-captured for the same result** —
  `eval/AGENTS.md` already forbids editing a ground-truth file after an experiment used it. The
  snapshot is that file here: it is what makes a number re-derivable without the app.

## Status

- [x] Branch, task note, design settled
- [x] `eval/rq1/measure.py`, `apps.json`, tests (31), README — `ae9ab25`
- [x] `eval/rq1/labelling.md` (ground-truth guide) — `ae9ab25`
- [x] `eval/pyproject.toml`: `rq1/tests` in `testpaths`, `rq1` in ruff's `src`
- [ ] **Capture + first numbers on the two pilots** — needs this machine free; the user asked
      on 2026-11-12 to run nothing on it this session.
- [ ] Post the first numbers to the team (third criterion)
- **Next step:** on this machine, with it otherwise idle, run
  `.venv/Scripts/python.exe eval/spikes/kp_state.py main` then
  `... eval/rq1/measure.py capture keepass2 --screen main`; repeat with `kp_state.py entry`
  and `--screen entry-editor`; start HandBrake and capture `main-summary`. Then
  `measure.py measure` for the first (unlabelled) numbers.

**43 eval tests pass and ruff is clean**, run here on 2026-11-12. The whole measuring half is
covered off Windows; nothing of the capture half has run against a real app yet, so
`UiaDesktop.list_windows()` filtering by `processName` and the multi-window naming are the two
places to watch on the first real run.

## Manual checks

- **(pending)** · hasan · capture the two KeePass 2 screens `kp_state.py` can reach plus
  HandBrake's main window, then `measure` · result: — · agreed with the user 2026-11-12: I
  capture what is scriptable, and the screens that need clicks (KeePass `options` and
  `open-database`, HandBrake's `main-video`/`preferences`/`queue`) come from a manual check
  posted on the issue.
- **(pending)** · hasan + a second labeller · label one screen per pilot per `labelling.md`,
  twice and independently, for the screen that goes into the report · result: —

## Open issues

- **Three copies of "the primary property set".** `client/src/shared/repository.ts`
  (`IDENTIFYING_FIELDS` + `suggestUses`, escalating, what ships), `agent/ayna_agent/model.py`
  (`PRIMARY_PRIORITY` + `primary_property()`, a single property, unused) and now this harness,
  which imports the agent's constant and appends `control_type` to reach the client's priority.
  They agree today only because I checked. Worth one issue: make one of them normative and have
  the others derive from or test against it. Not in #29's scope.
- `eval/pyproject.toml`'s `testpaths` is `apps/trial/tests` only, so a new test directory is
  invisible to CI until it is added. Adding `rq1/tests` here; the next experiment folder will
  hit the same thing.

## Decisions taken while building it

- 2026-11-12 — **`by` prefix on the rate CSV's property columns** — `byControlType` and
  `controlType` would otherwise be the same column name, and the row label silently lost to the
  counter. Caught by a test; the test stayed.
- 2026-11-12 — **`sys.stdout.reconfigure("utf-8")`** — the summary is a markdown table meant to
  be pasted into an issue and it carries Turkish control names; this console is cp1254 and
  turned the em dash into `?` before the fix.
- 2026-11-12 — **The label file is separate from the controls CSV, not a column in it** — the
  sheet is regenerated on every `measure` run, so a human's work cannot live in it.
- 2026-11-12 — **`conftest.py` adds `agent/` to `sys.path`, not just `measure.py`** — ruff sorts
  a test module's imports, and `from ayna_agent...` sorted *above* `import measure`, so the path
  could not depend on `measure` being imported first. It failed exactly that way once.

## Handoff

The `sys.path` insert at the top of `measure.py` is load-bearing and intentional: `eval/` has no
packages (`[tool.setuptools] packages = []`) and the agent is not an `eval` dependency, so the
import is by repository layout. If `agent/ayna_agent/model.py` or `playback/resolve.py` ever grow
a pywinauto import, this harness stops working off Windows and the CI test goes with it — both
modules say in their docstrings that they must not, and a test here pins it.

## Outcome (fill when the issue closes)
