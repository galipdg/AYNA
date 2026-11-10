# #22 Element under cursor + bounds

- Issue: https://github.com/galipdg/AYNA/issues/22
- Owner: hasan · Branch: `hasan/22-element-from-point`
- Started: 2026-11-10 · Last update: 2026-11-10

## Approach

`elementFromPoint(x, y)` answers **from the snapshot the agent last took of the window under the
point**, instead of deriving a descriptor from the hit element on its own. One UIA hit test
(`IUIAutomation::ElementFromPoint`), one Win32 `WindowFromPoint` + `GetAncestor(GA_ROOT)` for the
top-level handle, then a lookup in the cached document.

Why not derive the descriptor from the element alone: `model.describe_tree` needs the node's
siblings, its parent and the parent's siblings (`nearest_label` rules 2 and 3) and the whole
ancestor chain (`parent_path`). Reading those for one element costs a property read per sibling,
which is unbounded — picking a row in KeePass 2's entry list would read every other row — and,
worse, an element whose siblings were *not* read would come back with `nearestLabel: null`, which
is **indistinguishable from "this element has no label"**. The same element would then have two
different descriptors depending on whether a snapshot happened to be open. Answering from the
snapshot makes the descriptor *the same object* the client is already showing, which is also
exactly what the Spy needs: select the tree node it already has (recorded in `active.md` as the
shape omer can build against).

Reply shape, one shape for every outcome, never an error for a point:

| field | meaning |
|---|---|
| `handle` | top-level window under the point, or `null` when there is no window there |
| `bounds` | the hit element's rectangle, physical pixels, or `null` |
| `snapshotId` | the cached snapshot of that window, or `null` when none is held |
| `elementId` | the element in that snapshot (`"e8"`), or `null` |
| `element` | that snapshot's element descriptor, or `null` |

The three states the client can tell apart:
- `snapshotId` null → nothing captured for this window yet: offer to capture it.
- `snapshotId` set, `elementId` null → the window changed since the capture: offer to capture again.
- both set → select that node.

Matching inside the document: candidates are the elements whose stored `bounds` equal the hit
element's; one candidate wins outright with no further COM call, several are disambiguated with
`CompareElements` (pywinauto's `UIAElementInfo.__eq__`), and if none compares equal the **last in
pre-order** wins, because same-bounds candidates are a wrapper chain and the deepest is what
`ElementFromPoint` returned. The matching is a pure function over the document so it can be
tested on macOS.

## Decisions (small, local to this task)

- 2026-11-10 — **The descriptor comes from the cached snapshot, not from a fresh derivation.**
  Reason above: unbounded sibling reads, and a silently weaker `nearestLabel` would make one
  element have two descriptors. Consequence: `elementFromPoint` is only fully useful after a
  `snapshot` of the same window, which is the Spy's actual flow.
- 2026-11-10 — **`snapshot()` keeps the last window's document and live elements** so the lookup
  costs no extra cross-process calls during the walk. One window at a time; a new `snapshot`
  replaces it. Holding the COM pointers is what makes `CompareElements` possible later.
- 2026-11-10 — **A point with nothing under it is not an error.** The reply is the same shape with
  nulls, so the Spy has one code path. Only a host without UI Automation raises (`-32001`).
- 2026-11-10 — **`x` and `y` may be negative.** Virtual-desktop coordinates are signed (a maximised
  window reports `[-11, -11, …]`, `learnings.md` 2026-11-07), so the parameter check is "an int",
  not `_positive_int`.
- 2026-11-10 — The top-level handle comes from **Win32 `WindowFromPoint` + `GetAncestor(GA_ROOT)`**,
  not from walking UIA parents, so it is the same kind of handle `listWindows` reports
  (`EnumWindows`) and the client can match it to the window it has selected.

## Status
- [x] Task note and branch
- [ ] `recognition/uia.py`: `element_from_point`, the snapshot cache, the pure matcher
- [ ] `rpc.py`: `elementFromPoint` (galip's file — its own commit)
- [ ] `docs/agent-rpc.md`: the method (galip's content in my folder — its own commit)
- [ ] Unit tests on the matcher and the reply shape (any OS)
- [ ] `@pytest.mark.windows` test on the trial app: 10 controls, duration
- Next step: write `element_from_point` and the matcher in `recognition/uia.py`.

## Manual checks
- Acceptance criterion 3 (100 % and 150 % scaling) cannot be a test I run here: changing the
  display scaling needs a person at the machine. Planned as a manual check once the code is in.

## Open issues
- Acceptance criterion 2 is "response time under 300 ms". With the cached-snapshot design the call
  is one hit test plus a Python lookup, so the number should be small; it still has to be measured
  on Windows and recorded.
- The Spy's own overlay is a window too. If the pick hotkey fires while the overlay is over the
  cursor, `WindowFromPoint` returns the overlay. omer's overlay is click-through, so Win32 should
  skip it, but this is worth one step in the manual check.

## Handoff
Nothing yet.

## Outcome (fill when the issue closes)
