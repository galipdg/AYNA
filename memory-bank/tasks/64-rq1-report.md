# #64 RQ1: recognition rate on all pilot apps

- Issue: https://github.com/galipdg/AYNA/issues/64
- Owner: hasan · Branch: `hasan/64-rq1-report`
- Started: 2026-11-15 · Last update: 2026-11-15

## Approach

#29 built the harness and it is on `main`. #64 is the **report**: `eval/rq1/report.md`, with

1. the rate per app **and per control type**, each with a **Wilson 95 % interval**;
2. the unrecognised controls, with the reason each one failed;
3. a verdict on **NFR-27** — "at least 90 % of the standard controls in the pilot apps shall be
   recognised" (RS §3.3, RQ1, SC-06).

Wilson rather than the normal approximation because the RS says so (§4.1, ref [37]) and because
the normal interval is indefensible at these sizes: a screen with 35 of 35 recognised gives
`1.0 ± 0.0`, which claims certainty from 35 observations. Wilson gives `[90.1 %, 100 %]`, which
is the honest statement.

### The trap this report must not fall into

`measure --labels` mixes labelled and unlabelled screens in one app line, so KeePass 2 reads
99–100 % while **one of its four screens is labelled** (`active.md`, 2026-11-14 — I had to
retract a number over this once already). So:

- **only labelled screens enter any rate**, and
- the report states its own coverage next to every number: how many screens of the app are
  labelled, and how many controls that is.

A rate over two screens is a rate over two screens; NFR-27 is about "the pilot apps", and the
report must not let those two be read as the same thing.

## Status
- [x] Branch, task note, data model read (`measure.py`'s `Screen`/`Control` are reusable as is)
- [x] `wilson()`, checked against **numeric root-finding on the score equation it solves**, not
      against its own output — eight sizes agree to 1e-9
- [x] `report.py`: per-app, per-control-type, unrecognised list, NFR-27 verdict, coverage
- [x] `eval/rq1/report.md` generated, and a test asserts the committed file is what the
      generator produces, so it can never drift from the labels it summarises
- [x] 33 new tests; `eval` is **242 passed** under CI's own invocation
      (`eval/../.venv/Scripts/pytest.exe` from `eval/`, not `python -m pytest`), ruff clean
- [x] **PR #253 open** as *Part of #64* (it does not close it), both reviews requested, all
      six checks green
- Next step: nothing of mine on the code. What the criterion still needs is labelling, not
  code: five captured screens, the second labeller #29 owes, and a decision on KeePassXC.

## What the report says today

| | |
|---|---|
| Over every labelled screen | **39 of 41 = 95.1 %**, Wilson 95 % [83.9, 98.7] |
| HandBrake (`queue`) | 4 / 6 = 66.7 %, [30.0, 90.3] |
| KeePass 2 (`options`) | 35 / 35 = 100 %, [90.1, 100.0] |

**NFR-27 is not demonstrated**, and the report says so: 95.1 % is above 90, but the interval
reaches down to 83.9 %, so the data is also consistent with a true rate below the requirement.
Judging it on the point estimate would turn "we saw two failures in 41" into "at least 90 % of
the pilot apps' controls are recognised".

The two failures are the **nameless WPF `MenuItem`s** already known from #29 — and putting the
measured rows in front of me corrected my own note about them: the proposed set is
`{className}` **alone**, not `{className, parentPath}`. `propose` keeps a property only while
it narrows the match, and `parentPath` narrows nothing when both dropdowns share one `Menu`.
Corrected in `learnings.md`; it matters for #73, which would otherwise look for a parent-path
signal that was never proposed.

## State of the data (2026-11-15)

| | |
|---|---|
| Screens planned (`apps.json`) | 9 — HandBrake 3, KeePass 2 four, KeePassXC two |
| Screens captured | **7** (KeePassXC, the optional third pilot, has none) |
| Screens labelled | **2** — `handbrake-queue`, `keepass2-options` |

So the report can be generated and is worth generating, but it cannot yet answer NFR-27 for
"the pilot apps". Saying that plainly is part of the deliverable, not a reason to wait.

## Open issues
- **Five captured screens are unlabelled** and labelling is manual. It is also the part #29
  left owing a **second independent labeller**; a rate from one labeller is a provisional rate
  and the report will say so.
- **KeePassXC is captured nowhere.** It is the optional third pilot (D1, #21), so its absence
  does not block NFR-27 — but "all pilot apps" in this issue's title means P1 and P2 unless the
  team says otherwise.

## Handoff
Nothing yet beyond this note.

## Outcome (fill when the issue closes)
