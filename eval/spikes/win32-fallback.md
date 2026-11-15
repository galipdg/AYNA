# win32 backend fallback: measured, and not worth building (#23)

Trial, 2026-11-14, hasan, on the Windows machine. Question: when UI Automation exposes no usable
identifying property, can the **win32** backend identify the same element?

**Answer: no, and the reason is structural rather than a matter of tuning.** Of the two pilot
applications, the elements win32 can see are exactly the ones UIA already names, the number it
offers for them is literally the same number UIA published, and that number is **not stable
across runs** except in one case out of 74. Everything UIA cannot name has no window of its own,
so there is nothing for a fallback to query.

**Recommendation: do not build the fallback.** `model.NEVER_MATCH` and `model._GENERATED_ID` are
already making the right call, and the one genuine finding below is a question about
`_GENERATED_ID`, not about a second backend.

## How it was measured

`win32_probe.py` walks a window with the agent's **own** `recognition.uia.UiaDesktop`, so the UIA
side — including `nativeWindowHandle`, which the walk already records — is the product's and not a
second implementation. For every element that reports a window handle it then asks pywinauto's
`HwndWrapper` about that same HWND: class name, `control_id()` (`GetDlgCtrlID`), window text,
rectangle. **The HWND is the join key**, because it is the one identifier both views of an element
certainly share; geometry is not, which is the lesson #22 settled (identity decides, geometry only
locates).

"UIA identifies" below means the model's own rule: an `automationId` that is present and is not
rejected by `_GENERATED_ID`. "win32 adds a number" means a **non-zero** control id that is
**different** from that `automationId` — a zero is Windows' "this window has no control id", and
the same number arriving by another road is not an addition.

| | KeePass 2 (WinForms) | HandBrake 1.11.2 (WPF) |
|---|---|---|
| Screen | main window, database open | main window |
| Elements | 74 | 149 |
| UIA identifies | 16 | 40 |
| **Has an HWND** | **16** | **1** |
| **win32 adds a number UIA did not** | **0** | **0** |

Runs: `win32-keepass2-main-run1.json`, `win32-keepass2-main-run2.json` (two separate launches),
`win32-handbrake-main.json`.

## Finding 1 — WPF gains nothing, and it cannot

HandBrake has **149 elements and exactly one HWND**: the window itself. A WPF window renders its
whole control tree into one window handle, so none of its 148 controls is a window and the win32
backend cannot address any of them. The 109 elements UIA cannot identify here — 76 `Text`, 11 of
the 20 `Button`s, 5 `MenuItem`s, 2 `Custom` — are therefore out of reach by construction, not by
accident.

This is the "which control types do **not** gain" half of the acceptance criterion, and for WPF the
answer is **every one of them**. The same holds for any framework that draws its own controls:
WPF, and the Qt widgets measured in `grid-probes.md`.

(The HandBrake run has 149 elements, which #29 identified as the source-picker state rather than
the clean `main-summary` one. It makes no difference here: the HWND count is a property of the
framework, not of the screen.)

## Finding 2 — in WinForms, win32's control id *is* UIA's AutomationId

In KeePass 2, **16 of 74 elements have an HWND, and for every one of them UIA's `automationId` and
win32's `GetDlgCtrlID` are the same value**:

| element | type | UIA `automationId` | win32 `control_id` | win32 class |
|---|---|---|---|---|
| `e2` | Pane | `199002` | 199002 | `WindowsForms10.Window.8.app…` |
| `e4` | Pane | `264544` | 264544 | `WindowsForms10.Window.8.app…` |
| `e13` | Pane | `133464` | 133464 | `WindowsForms10.Window.8.app…` |
| `e33` | Pane | `264604` | 264604 | `WindowsForms10.Window.8.app…` |
| `e57` | ComboBox | `133458` | 133458 | `WindowsForms10.COMBOBOX.app…` |
| `e58` | Edit | `1001` | 1001 | `Edit` |

So a fallback would hand back the number the snapshot already contains. There is no second source
of identity here — there is one number, reachable two ways.

## Finding 3 — the number is not stable, which is why rejecting it is right

Two launches of KeePass 2 at the same screen, matched on `(controlType, name, className)`:

| | |
|---|---|
| matched elements | 59 |
| `automationId` unchanged | 58 |
| **win32 control id unchanged** | **1** |
| win32 control id changed | **7** |
| `nativeWindowHandle` unchanged | **0** |

`m_lvEntries`'s control id went `133448 → 199024`, the menu bar's `1050938 → 264538`, the tree's
`264548 → 330084`. These are **handle-derived values, not designer-assigned ids** — they move with
the window handles, exactly as `NEVER_MATCH` says of `native_window_handle` ("session-scoped: a new
handle every run"). A fallback that stored one would be wrong on the next launch, which is worse
than having no identity: it would resolve to the wrong element or to none, silently.

`e57` is the instructive case: its `automationId` itself changed (`133458 → 3606620`), so it is the
one element whose UIA identity moved — and win32's control id moved with it, to the same new value.
Both backends are reporting the same unstable thing.

## Finding 4 — the one real gain is a question about `_GENERATED_ID`, not about win32

Exactly **one** element kept its control id across the restart: `e58`, a **native Win32 `Edit`**
(class name `Edit`, with no `WindowsForms10.` prefix) carrying **`1001`** both times. That is a
compiled-in dialog control id, and it is genuinely stable identity.

And `model._GENERATED_ID` rejects it, because it is a bare number — "a Win32 control id (`1001`)"
is that pattern's own first example. So for this element the project is discarding usable identity.

But note what the fix would **not** be: win32 adds nothing here either, since UIA already publishes
`1001` as the `automationId`. The change, if any, is to **trust a bare number when it comes from a
native Win32 class** and not when it comes from a `WindowsForms10.*` one. Before anyone acts on
that:

- the sample is **one element**, and a rule in `model.py` is **normative under #11** (healing
  recomputes a descriptor from a stored snapshot), so changing it needs an ADR and a
  `FEATURE_VERSION` bump that touches galip's scorer;
- the class-name test would have to be measured on more native-Win32 dialogs than KeePass 2's one
  search box before it could be called a rule rather than a coincidence.

Recorded as an open issue on #23 rather than done here.

## What this says about where recognition can actually improve

The population #23 was aimed at — elements UIA cannot identify — is **58 of 74** in KeePass 2 and
**109 of 149** in HandBrake, and **almost none of them is a window**: every toolbar `Button`, every
`MenuItem`, `TreeItem`, `ListItem`, `Separator` and `Text` in KeePass 2 has no HWND. A second
backend was the wrong place to look. What #29 measured on the same applications points at the real
levers: composite controls whose inner parts a tester never targets (handled by labelling), and
nameless elements whose identity sits on an **ancestor** (HandBrake's `MenuItem`s inside a named
`Menu`), which is a descriptor question, not a backend one.

## Reproducing it

```powershell
# the UIA side needs the AGENT's venv: the recognition backend reaches `ayna_agent.rpc`
# for its exception types, which imports `websockets`
.venv/Scripts/python.exe eval/spikes/kp_state.py main          # KeePass 2, database open
agent/.venv/Scripts/python.exe eval/spikes/win32_probe.py probe --process KeePass.exe `
    --json eval/spikes/win32-keepass2-main-run1.json
# restart the pilot copy only (kp_state.kill_pilot), reach the same state, probe again, then:
agent/.venv/Scripts/python.exe eval/spikes/win32_probe.py compare `
    eval/spikes/win32-keepass2-main-run1.json eval/spikes/win32-keepass2-main-run2.json
```

`compare` runs on any OS from the saved files, and the pure parts are tested in
`test_win32_probe.py` (19 tests). Three of those tests exist because the probe got these wrong
first: a zero control id counted as "stable", `None` in a match key crashed the comparison on
every real run, and absent handles counted as "the handle did not move" — which had reported 49
stable handles and read as evidence against `NEVER_MATCH`.
