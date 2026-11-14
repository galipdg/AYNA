# #40 Playback v1: all keywords + smart waits

- Issue: https://github.com/galipdg/AYNA/issues/40
- Owner: hasan · Branch: `hasan/40-playback-v1`
- Started: 2026-11-14 · Last update: 2026-11-14

## Where #26 left it

`playback/runner.py` already has the shape: resolve with a deadline, act, record one result,
stop the run on a failure. `IMPLEMENTED = frozenset({"Click", "Type"})` and every other keyword
fails by name saying "#40". So this issue is a **delta**, not a rewrite:

| keyword | #26 | #40 |
|---|---|---|
| `Click`, `Type` | done | unchanged |
| `Wait` | fails | wait until the target is *ready*, then pass |
| `Select` | fails | choose the item whose text is `value` |
| `Verify` | fails | the checkpoint: 9 properties × 3 operators, re-read until it holds |
| `SelectRow` | fails | select the row `row` addresses |

The schema on `main` is **0.2** (galip's v0.2 merged), so `SelectRow` and the three row
checkpoints (`cell`, `rowExists`, `rowCount`) are part of v1 whether or not the issue text lists
them — the step editor already produces them (omer's #220), and a document playback cannot read
is worse than a keyword that is not offered.

## The one real gap in #26's waiting, and it is in the issue text

The issue says "before each step wait until the element **exists, is visible and enabled**".
`_resolve_waiting` waits only until the target *resolves*: a disabled or offscreen element
resolves immediately, and the step then fails in `actions` instead of waiting for the control to
become usable. The schema uses the same word for this — `timeoutMs` is "longest wait for the
target … to become **ready**", and `Wait` is "only wait until the target is ready".

So **"ready" = resolves to exactly one element, and is not disabled, and is not offscreen**, and
it is the pre-step wait for *every* keyword, not a `Wait`-only idea. `Resolution` already carries
the `descriptor`, whose `enabled` and `offscreen` come from the same re-read, so this costs
nothing extra per poll.

HandBrake gives the real example from #29: with no source loaded **every** tab reads
`enabled: false`. Under #26's rule a step targeting one fails instantly with an action error;
under this rule it waits out its timeout and then says the control never became enabled, which is
what a tester needs to read.

`enabled`/`offscreen` are `None` when the provider did not report them. `None` must count as
**ready**, not as not-ready: refusing to act on an element whose state could not be read would
make playback depend on a property `NEVER_MATCH` already calls unreliable.

## Decisions (small, local to this task)

- 2026-11-14 — **"Ready" gates every keyword, and a `Verify` is the exception** — a checkpoint
  whose whole purpose is `enabled: false` or `visible: false` would be unplayable if the runner
  refused to look at a disabled element. So a `Verify` step waits only for *resolution*, and the
  checkpoint itself is what re-reads. `Wait`, `Click`, `Type`, `Select` and `SelectRow` wait for
  ready.
- 2026-11-14 — **Keep `within N ms` for element-not-found** even though the issue's third
  criterion says "after N ms". #26 shipped `within`, it is tested, and omer's run report (#59)
  renders it; a checkpoint that ran out of time says `after N ms`, which is the wording I
  committed to in the PR #231 review. Two different waits, two words, both deliberate. Noted on
  the issue rather than changed silently.
- 2026-11-14 — **A checkpoint re-reads on its own deadline, like resolution does** — the schema
  says `timeoutMs` covers "the target (and for SelectRow and row checks, its row or check)
  becoming ready". The same `POLL_INTERVAL_S` (250 ms) and the same deadline, so a property that
  is about to change is not a race.
- 2026-11-14 — **Message wording is fixed and comes from the #231 review**, not invented here:
  `login.message: name should contain "Invalid", it is "Welcome, admin!"`,
  `login.okButton: enabled should be true, it is false`,
  `main.customerGrid: rowCount should be 3, it is 5`,
  `main.customerGrid: a row with "Yılmaz" in "Soyad" should exist, none does`. Lower case,
  logical name first, no "Step failed:" prefix, ` after N ms` appended when it re-read until the
  time ran out. **#40 must use exactly these** — I promised omer they would, and his seed data
  and the report's tests are written against them.

## Status

- [x] Branch, task note, the delta and the "ready" design
- [x] `Wait` + the ready gate — `826b386`
- [x] `Verify` for the six element properties — `playback/checkpoint.py`
- [ ] `Select`
- [ ] `SelectRow` and the three row checkpoints
- [ ] The three acceptance criteria, each with its own test
- Next step: `Select` — the design is below, so it does not need re-deriving.

### `Select` is not a pure action, and that is the design

`actions.click` and `actions.type_text` each get **one** element and act on it. `Select`
cannot: "choose the item whose text is `value`" needs the *item*, which is a descendant of the
target, and on a combo box **the items may not exist until it is expanded** (#33 measured
exactly this on Qt). So the flow belongs in the runner, where the tree and the re-read live:

1. resolve the target and wait for ready (already done by the time the keyword is reached);
2. look for a descendant of the target whose text is `value` in the tree just read;
3. if there is none and the target has `ExpandCollapse`, expand it, **re-read the tree**, and
   look again — the re-read is the point, because the items are new elements;
4. `SelectionItem.Select()` the item; `Invoke` as a fallback (a menu item answers to Invoke);
5. collapse again if step 3 expanded it, so the screen is left as the test found it;
6. if the target is an editable combo box and none of that worked, `Value.SetValue(value)` —
   last, because it writes text rather than choosing an item, and a combo box that accepts
   arbitrary text would otherwise hide a genuine "no such item".

An item's text: `ValuePattern` value when non-empty, else the UIA Name — **the same rule the
schema already states for a cell** ("a cell's text is its ValuePattern value when that value is
non-empty, else its UI Automation Name"), so `Select` and the row checks share it rather than
each inventing one. That rule belongs in one place both can import.

**The failure must distinguish three things**, because a tester fixes each differently: the
target is not a list or combo box at all; it is, and has no item with that text (say how many
items it does have); and it has the item but the provider refused to select it. The third is
the Qt case and is a finding about the framework, not about the test.

**Expect Qt to refuse** (`active.md`, from #33): `SelectionItem.Select`, `Invoke` and
`ValuePattern.SetValue` all leave a Qt combo box unchanged, and the items only exist after
`ExpandCollapse`. **SC-20 needs `Select` on a combo box**, so if it still refuses after the
expand-and-re-read above, that is a real obstacle for a reference scenario: report it on #40
and raise it for SC-20 rather than faking a pass. Measure it on the sample app (#33) before
concluding anything — the earlier finding was made without the expand-then-re-read step.

### What `Verify` turned out to need

- **Three of the six properties are not in a descriptor and are read live**: `value`
  (`ValuePattern`, then `LegacyIAccessible` — the same ladder `Type` writes down), `checked`
  (`TogglePattern` state is **On**, so indeterminate is *not* checked) and `selected`
  (`SelectionItemPattern`). `name`, `enabled` and `visible` come from the descriptor the walk
  already derived, so they cost nothing beyond the read the runner did.
- **"Cannot be read" is its own failure, not `false`.** No `TogglePattern` on the target, or a
  provider that does not report `IsEnabled`: there is no answer, and reporting "expected true,
  got false" would tell a tester their application is wrong when it is the check that does not
  apply.
- **An empty expectation has to match an element with no text.** `expected: ""` is a real check
  ("the error label is empty") and a nameless target reads as `None`, so `_same` compares
  `actual or ""` against a string expectation. Otherwise an empty label could never be verified.
- **A target that disappears mid-check reports that**, not a property failure: "it was there and
  now it is not" is a different fact and a tester debugs the two differently.
- **The target is resolved again on every poll** rather than kept. A re-read gives new live
  elements and holding the old one would read a stale handle — the same reason #22's
  `elementFromPoint` compares identity instead of trusting a remembered element.

## Open issues

- **UI Automation cannot choose an item in a Qt combo box** (from #33, recorded in `active.md`):
  `SelectionItem.Select`, `Invoke` and `ValuePattern.SetValue` all leave it unchanged, and the
  items only exist after `ExpandCollapse`. **SC-20 needs `Select` on a combo box**, so this is a
  real obstacle for one of the reference scenarios rather than a detail. Plan: implement `Select`
  through the patterns ladder, expand first when the target offers `ExpandCollapse`, and if Qt
  still refuses, report it on #40 and raise it for SC-20 rather than faking a pass.
- `cell` is grid-only in the schema while `rowExists {value, column}` is allowed on a list — the
  same column mapping, one forbidden and one required. Raised on #220/#221; galip's v0.2 ADR to
  settle. Playback implements what the schema says and the asymmetry stays visible.

## Manual checks

- (pending) · the Windows half: every keyword against the sample app (#33) and the two pilots,
  including the Qt combo box and a KeePass 2 row.

## Handoff

## Outcome (fill when the issue closes)
