# RQ1 — recognition measurement

**RQ1:** of the controls a tester would want to automate on a pilot app's screen, how many can
AYNA identify uniquely from an element descriptor? Issue #29 builds the harness; **#64** runs it
on all pilot apps and reports the result.

```powershell
# setup, once, from the repository root
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e "eval[dev]"

# 1. put the pilot app in the state apps.json describes, then capture that screen (Windows)
.venv/Scripts/python.exe eval/rq1/measure.py capture keepass2 --screen entry-editor

# 2. write the CSVs and print the table (any OS, from the committed snapshots)
.venv/Scripts/python.exe eval/rq1/measure.py measure
.venv/Scripts/python.exe eval/rq1/measure.py measure keepass2 --labels

# tests
.venv/Scripts/python.exe -m pytest eval/rq1/tests
```

`measure` with no app measures the D1 pilots, **HandBrake** and **KeePass 2**; KeePassXC is in
`apps.json` but off by default, because D1 makes the third pilot conditional. Name an app id to
measure it alone.

## What is here

| Path | What it is |
|---|---|
| `measure.py` | The harness: `capture` (Windows, UIA) and `measure` (pure). |
| `apps.json` | Pilot apps, their processes, and the screens RQ1 measures with the state each must be in. |
| `labelling.md` | The ground-truth procedure: how a person enumerates a screen's controls, and what `control` / `ignore` / `missing` mean. |
| `snapshots/<app>/<screen>.json` | What a capture wrote. **The evidence**: every number is re-derivable from these without the applications. Frozen once a result used one. |
| `labels/<app>-<screen>.csv` | `elementId,label,note` from `labelling.md`. Frozen the same way. |
| `results/<app>-<date>-rates.csv` | Per control type: controls, recognised, share, ambiguous, no-property, and which property carried each set. |
| `results/<app>-<date>-controls.csv` | One row per control: the evidence behind every rate, and the sheet a person labels. |

## How "recognised" is defined

Build the primary property set the **Spy** would propose for the control (the priority of
`automationId`, `name`, `nearestLabel`, `className`, `parentPath`, `controlType`, a property kept
only while it narrows the match, a generated `automationId` skipped), then count the elements of
the **same window** that match it. Exactly one match is recognised.

The harness imports `ayna_agent.model` and `ayna_agent.playback.resolve` rather than
re-implementing either, so the rule and the comparison are the product's own; both modules are
free of UI Automation by contract, which is why the measuring half runs and is tested off
Windows. `tests/test_measure.py` fails if that stops being true, if the client's property
priority changes, or if #6's interactive set changes — a number is only comparable with an older
one while those definitions hold.

**A control** is #6's interactive set (15 control types) with the window frame excluded, kept
identical to `eval/spikes/uia_tree_dump.py` so these numbers sit beside the D1 table in
`eval/spikes/uia-dump.md`.

**Report the labelled rate.** Without `--labels` the denominator is only what AYNA's walk found,
so a control the walk missed is invisible and the rate flatters us. The harness says which
denominator it used in the heading of every table it prints.
