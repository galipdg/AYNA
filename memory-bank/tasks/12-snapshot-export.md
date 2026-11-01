# #12 Window snapshot export

- Issue: https://github.com/galipdg/AYNA/issues/12
- Owner: hasan · Branch: `hasan/12-snapshot-export`
- Started: 2026-11-01 · Last update: 2026-11-01

## Approach
Two commits, in this order, and the order is the one decision that mattered:

1. **The contract first** — `schemas/snapshot.schema.json`, one real example and the ADR. Ömer
   asked for exactly this on #12 on 2026-10-31 and again on 2026-11-01: #15 (snapshot import,
   due this week), #24 and #25 (Spy tree and property panel) and through them the G0 demo (#28,
   9 November) were waiting on the *shape*, not on the code. The handoff from the previous
   session had the backend first; that would have left three issues blocked another day.
2. **The UIA backend** for #16 — `list_windows()` and `snapshot(handle, timeout_ms)`, which is
   what `rpc.py` already has a `Desktop` protocol and an `UnavailableDesktop` placeholder for.

The pure part (`recognition/snapshot.py`) reads no UI Automation: it turns the raw nodes of a
walk into the document, so the shape is tested on any OS and replayed over the #6 dumps, exactly
as `model.py` does for the descriptor. The example is **rebuilt by the tests** from the same
captured trial-app tree the descriptor tests use (`agent/tests/data/trial-app-tree.json`), so
the file other components design against cannot drift away from the agent that writes it.

The budget comes straight out of #161 (`eval/spikes/uia-walk-cost.md`, PR #170): 17 plain
properties + `LabeledBy`, no pattern probes, 5 000 ms as a deadline **on a timer**, dedup by
window handle with owner-first roots.

## Decisions (small, local to this task)
- 2026-11-01 — Schema and example before the backend — three issues and the G0 demo were blocked
  on the shape; #170's measurements already pin every number the schema needs.
- 2026-11-01 — Flat `elements` array in pre-order with `{id, parentId, element}`, not nested
  children — a healing candidate must name one element by id (#149), `describe_tree` and the #6
  dumps are flat already, and #15/#24 build the tree in one pass.
- 2026-11-01 — Element ids are `e<position>`, opaque — stable inside a document, never parsed or
  compared across documents. Same `opaqueId` definition as the healing proposal.
- 2026-11-01 — The descriptor is **duplicated** from `element.schema.json`, not `$ref`-ed — a
  `urn:` `$ref` needs a resolver registry in Java, TypeScript and Python; the healing proposal
  set that precedent with `scoredElement`. A test compares both property maps including
  constraints, so they cannot drift.
- 2026-11-01 — No `truncated` flag, no depth or element limit: one failure state (`-32002`, no
  document). A partial tree is the one input FR-29 forbids healing to rank from.
- 2026-11-01 — `app` is `{exeName, fileVersion}` and the server's Application/AppVersion names
  stay a human choice at import; the exe **path** is left out because it names the user.
- 2026-11-01 — `FEATURE_VERSION = "features-v0"` lives in `recognition/snapshot.py` until #43
  creates `heal/features.py`; there must only ever be one. Noted in galip's inbox.
- 2026-11-01 — `dumps` is canonical (fixed key order, 2-space indent, LF, UTF-8 unescaped), so
  the round trip of criterion 3 holds even for a file whose keys arrived in another order.

Full reasoning: `memory-bank/decisions/2026-11-01-snapshot-schema-v0.md` (Proposed, needs all
three approvals).

## Status
- [x] `schemas/snapshot.schema.json` version 0.1
- [x] `schemas/examples/snapshot/trial-login.json` (the trial app's login window, 14 real
      elements) and `cases.json` (8 valid + 31 invalid named cases)
- [x] `agent/ayna_agent/recognition/snapshot.py`: `build`, `canonical`, `dumps`, `loads`,
      `read`, `write`, `DEFAULT_BUDGET_MS`, `FEATURE_VERSION`
- [x] `agent/tests/test_snapshot.py` — 71 tests. Whole agent suite 256 passed, `ruff check` and
      `ruff format --check` clean (run 2026-11-01 on this machine)
- [x] ADR + `decisions/README.md` line; `schemas/README.md` sections for the element descriptor
      (missing since #11) and the snapshot; `docs/agent-rpc.md` success example for `snapshot`
- [x] Removed a stray `<<<<<<< HEAD` marker that a `copilot-swe-agent[bot]` merge left in
      `memory-bank/decisions/README.md` and that reached `main`
- [ ] UIA backend: `recognition/uia.py` with `list_windows()` and `snapshot(handle, timeout_ms)`,
      `setup()`/`close()` on the `ayna-uia` thread, per-monitor-v2 DPI awareness, dedup by handle
      with owner-first roots, the deadline on a timer
- [ ] Swap `UnavailableDesktop(...)` for it in `rpc.main()` (one line; galip said it is fine for
      me to change)
- [ ] Criterion 1 — "snapshot of the trial app under 2 s" — needs the backend and a measurement
      on this machine; **not ticked**
- Next step: `agent/ayna_agent/recognition/uia.py`. Reference for the walk, the reader and the
  window enumeration: `eval/spikes/uia_dump.py` (`walk`, `UiaReader`, `find_windows`,
  `exe_info`, `window_dpi`); for owner-first roots and the per-element timing,
  `eval/spikes/uia_probe.py` (`owner_first`, `nesting_order`) on `hasan/161-winforms-walk`. Emit
  nodes with `sibling_index` (not `index`) and `labeled_by`, which is what `describe_tree` reads.

## Manual checks
- Pending: capture the trial app's login window through `snapshot` and confirm criterion 1
  (under 2 s) and that the document equals the committed example apart from `snapshotId`,
  `capture` and the session-scoped `handle`/`processId`. Needs the backend first.

## Open issues
- **`minLength: 1` cannot say "not only spaces".** Both `snapshot.schema.json` and
  `element.schema.json` promise that a whitespace-only string is never stored and only enforce
  non-empty. The agent honours it (`model._blank`); a Java or TypeScript producer could write
  `"   "` and be valid. Named as a *valid* case in `examples/snapshot/cases.json` so the gap is
  visible, and raised under "Open, for the deciders" in the ADR. Recommendation: add
  `"pattern": "\\S"` to every string property in **both** schemas in one PR that bumps both to
  0.2, after #15 and #24 have landed against 0.1.
- **`pywin32` cannot be an unconditional dependency.** PyPI has only Windows wheels, so
  `pip install -e ".[dev]"` in `agent/` would fail outright on galip's and omer's macOS
  machines. The user chose "unconditional" before knowing this; to settle when the backend
  lands. `eval/pyproject.toml` already uses `; sys_platform == 'win32'` for pywinauto.
- **`schemas/AGENTS.md` says only the step schema's tests, in `ai/`.** The element and snapshot
  schemas are tested in `agent/` (CI job `agent`). Needs a line, but it is an `AGENTS.md`, so
  ask the user first.
- The element-descriptor ADR still says `Proposed (#11)` although #11 closed with three
  approvals (PR #175). Someone has to flip it to Accepted.
- `schemas/README.md` and this ADR point at `eval/spikes/uia-walk-cost.md`, which is still on
  `hasan/161-winforms-walk` (PR #170). Written as a forward reference, not a link, so nothing is
  dead on `main`; make it a link once #170 merges.

## Handoff
- The two schema files, the example and the ADR are what ömer needs; tell him on #12 that the
  field names can still move until the ADR is accepted, and that `elements` is **flat with
  parent ids**, which was his explicit question.
- `rpc.py`'s `Desktop` protocol is the exact interface to implement; `rpc.SnapshotTimeout`,
  `WindowNotFound` and `UiaUnavailable` already exist and already map to -32002 / -32000 /
  -32001. The backend must import pywinauto **inside** `setup()` or the first call, because COM
  has to be initialised on the `ayna-uia` thread, not at module import.
- The deadline cannot be enforced only between elements: under a modal message box one
  `FindAll` blocked for 72 s (#161). Plan for a timer that abandons the walk.

## Outcome (fill when the issue closes)
