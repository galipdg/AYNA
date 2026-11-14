# #23 win32 backend fallback trial

- Issue: https://github.com/galipdg/AYNA/issues/23
- Owner: hasan · Branch: `hasan/23-win32-fallback`
- Started: 2026-11-14 · Last update: 2026-11-14

## Approach

The issue says "when UIA exposes no usable identifying property, query the win32 backend for the
same element". It is titled a **trial**, so the order is: measure what win32 actually exposes
that UIA does not, *then* decide whether a fallback is worth building. Writing the fallback first
would be assuming the answer.

`eval/spikes/win32_probe.py` walks a window with the agent's **own** `recognition.UiaDesktop`
(so the UIA side is the product's, including `nativeWindowHandle`, which the walk already
records), then for every element that reports a window handle asks the **win32** side about the
same element through `pywinauto.controls.hwndwrapper.HwndWrapper`: class name, `control_id()`
(`GetDlgCtrlID`), window text, rectangle. The join key is the HWND, which is the only thing the
two backends certainly agree on.

## What makes this question sharper than the issue text

Two facts already in the code decide most of it, and the trial is really about whether they hold:

1. **`model.NEVER_MATCH` already says `native_window_handle` is "session-scoped: a new handle
   every run"**, so a fallback that merely finds the element by HWND gains **nothing** for
   identification. Whatever win32 contributes has to be stable across runs to count.
2. **`model._GENERATED_ID` already rejects a bare number as an AutomationId** — "a Win32 control
   id (`1001`)" is its own first example. For a Win32/WinForms control UIA's `AutomationId`
   usually *is* the control id, so win32's `GetDlgCtrlID` would hand back the same number the
   model deliberately throws away.

So the decisive measurement is **not** "can win32 see the element" but **"is the number stable
across runs?"** If a WinForms numeric id is the same on every launch, the model is discarding
usable identity and the fix is a scoring change, not a second backend. If it changes per launch,
`_GENERATED_ID` is right and a win32 fallback cannot help either. Either way the answer is the
report the issue asks for. The probe therefore has a `compare` mode for two runs of the same
screen.

This is also exactly #29's open case: KeePass 2's Options → Security has four `NumericUpDown`
composites whose 16 inner parts carry generated numeric ids (`1050270`) and are the only
ambiguous controls on that screen.

## Decisions (small, local to this task)

- 2026-11-14 — **Measure before building the fallback** — the issue is a trial and the two facts
  above make it likely that win32 adds nothing. A fallback written first would be a feature
  nobody can justify, and it would sit in the recognition path forever.
- 2026-11-14 — **Join the two backends by HWND, not by geometry or by name** — it is the one
  identifier both views of an element certainly share. Geometry would repeat the mistake #22
  settled (identity decides, geometry only locates).
- 2026-11-14 — **Pilots: KeePass 2 (WinForms) and HandBrake (WPF)** — the criterion asks which
  control types gain and which do not, and WPF is the "do not" half by construction: a WPF
  window is one HWND, so win32 sees no controls inside it at all. Measuring both is what makes
  the answer a list rather than an opinion.

## Status

- [x] Branch, task note, design
- [x] `eval/spikes/win32_probe.py` and 19 off-Windows tests
- [x] KeePass 2 (WinForms) twice from two separate launches, HandBrake (WPF) once
- [x] `eval/spikes/win32-fallback.md` — the report both criteria ask for
- [ ] Post the answer on #23 and open the PR
- Next step: post the report's summary on #23, then the PR. **The fallback itself is
  deliberately not built** — see below.

## The answer: do not build it

**The elements win32 can see are exactly the ones UIA already names, the number it offers is the
same number UIA published, and that number is not stable across runs.** Everything UIA cannot
name has no window of its own.

| | KeePass 2 (WinForms) | HandBrake (WPF) |
|---|---|---|
| Elements | 74 | 149 |
| UIA identifies | 16 | 40 |
| **Has an HWND** | **16** | **1** |
| **win32 adds a number UIA did not** | **0** | **0** |

1. **WPF cannot gain anything, structurally.** 149 elements, **one** HWND — the window. All 148
   controls are drawn into it, so win32 can address none of them. Same for Qt. That is the
   "which control types do not gain" half of criterion 2, and the answer is "every one".
2. **In WinForms, win32's `GetDlgCtrlID` *is* UIA's `automationId`** — identical for all 16
   elements that have an HWND (`e2` 199002/199002, `e58` 1001/1001, …). One number, two roads.
3. **It is not stable.** Across two launches: 59 matched elements, `automationId` unchanged 58,
   **win32 control id unchanged 1, changed 7**, `nativeWindowHandle` unchanged 0. `m_lvEntries`
   went 133448 → 199024. They are handle-derived, exactly as `NEVER_MATCH` says. A fallback
   would store a value that is wrong on the next launch — worse than no identity, because it
   resolves silently to the wrong element or to none.
4. **The one genuine gain is not about win32 at all.** Exactly one element kept its control id:
   `e58`, a **native Win32 `Edit`** (class `Edit`, no `WindowsForms10.` prefix) with **1001**
   both times — a compiled-in dialog id, real identity, and `_GENERATED_ID` throws it away
   because it is a bare number. The fix, if any, is to trust a bare number from a native Win32
   class and not from a `WindowsForms10.*` one. See "Open issues": one element is not a rule.

**Where recognition can actually improve**, since this was the wrong place to look: the
unidentified population is 58/74 and 109/149, and almost none of it is a window — every toolbar
`Button`, `MenuItem`, `TreeItem`, `ListItem` and `Text` in KeePass 2 has no HWND. #29's findings
on the same two applications point at the real levers: composite controls (labelling handles
them) and nameless elements whose identity sits on an **ancestor**, which is a descriptor
question.

## Open issues

- **`_GENERATED_ID` rejects stable native-Win32 control ids along with unstable WinForms ones.**
  `e58` (`Edit`, `1001`) is real identity being discarded. The candidate rule is a class-name
  test: trust a bare number from a native Win32 class, not from `WindowsForms10.*`. **Sample
  size one**, and `model.py` is **normative under #11** (healing recomputes a descriptor from a
  stored snapshot), so it needs an ADR and a `FEATURE_VERSION` bump touching galip's scorer.
  Worth its own issue after it is measured on more native-Win32 dialogs; not a change to slip
  into this trial.
- **`eval/spikes/` has no CI job and is excluded from ruff** (`eval/pyproject.toml`'s
  `extend-exclude`), so `test_win32_probe.py`'s 19 tests only run when someone names the path.
  Same gap `active.md` already records for the other spike tests; worth one issue with the
  `testpaths` one.
- `UiaDesktop()` needs `setup()` called by hand in a script — the RPC server normally does it
  once on its worker thread. Both #29's harness and this probe hit it. A one-line note in
  `agent/AGENTS.md` would save the next person the traceback.

## Manual checks

- **DONE** · 2026-11-14 · hasan, on this machine · two launches of KeePass 2 at the main window
  with the demo database open (via `kp_state.py main`, restarted with `kp_state.kill_pilot()`
  between them, which kills the pilot copy by image path only), plus one HandBrake run ·
  evidence: `eval/spikes/win32-keepass2-main-run{1,2}.json`,
  `eval/spikes/win32-handbrake-main.json`, written up in `eval/spikes/win32-fallback.md`.
  Display at 125 %, KeePass 2.61.1, HandBrake 1.11.2, Windows 11 Pro 10.0.26300.
- **Not done, and not needed for the answer:** KeePass 2's Options → Security screen, which is
  where #29's 16 composite inner parts live. It would need the user to stage the screen twice,
  and the main window already answered the question structurally — those inner parts are
  `Spinner`/`Button` children of a WinForms composite, and the main window shows that class of
  element either has no HWND or carries a handle-derived id. Worth doing only if someone
  disputes finding 3.

## Handoff

The probe's three corrected bugs are each pinned by a test and are the kind that flatter a
fallback rather than break it, so do not "simplify" them away: a zero `control_id` counted as
stable; `None` in a match key crashed `compare` on every real run (a nameless element is the
whole population here); and absent handles counted as "the handle did not move", which reported
49 stable handles and read as evidence against `NEVER_MATCH`.

## Outcome (fill when the issue closes)
