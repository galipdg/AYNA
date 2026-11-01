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
- [x] UIA backend `recognition/uia.py`: `UiaDesktop` with `setup()` / `close()` on the
      `ayna-uia` thread, `list_windows()`, `snapshot(handle, timeout_ms)`, per-monitor-v2 DPI
      awareness, dedup by window handle, 12 properties per element, the deadline on a timer
- [x] `rpc.main()` uses it instead of `UnavailableDesktop`
- [x] `agent/tests/test_uia.py` — 24 tests: 20 with fakes (any OS) and 4 `@pytest.mark.windows`.
      Whole suite **280 passed**, the macOS selection 276 passed / 4 deselected, ruff and format
      clean (run 2026-11-01 on this machine)
- [x] **Criterion 1 met and measured**: the trial app's login window, 14 elements, **28–32 ms
      over six runs** (median 28.5, 2.04 ms per element) against the 2 s bound. Also measured:
      KeePass 2's main window **114 elements in 819 ms** and its `Add Entry` dialog 40 in 363 ms
- [x] End-to-end through the RPC: `ping`, `listWindows` (9 windows), `snapshot` returning a
      document that validates against the schema (14 elements, 31 ms of 5 000 ms), `-32000` for
      a closed handle, `-32002` for a 1 ms budget, `-32602` for an unknown param, exit 0 when
      stdin closes. So #16's remaining condition (`snapshot` answers through it) is met
- Next step: open the PR with `Closes #12`, request galip's and omer's review (the ADR needs all
  three), comment on #12 that omer's two requests are answered, and ask galip to close #16 or
  say what else it needs.

## Manual checks
All on this machine, `Windows-11-10.0.26300`, DPI 120 (125 % scaling), Python 3.13.0,
pywinauto 0.6.9. The numbers are repeated in `learnings.md` so they survive this note.

- 2026-11-01 · hasan · `list_windows()` on the real desktop · **pass** · 8–9 visible top-level
  windows, cloaked ones filtered out, every field of the `listWindows` contract present.
- 2026-11-01 · hasan · criterion 1, trial app login window · **pass** · 14 elements,
  28/30/28/28/28/29 ms over six runs; the tree, the control types and the two `geometric`
  labels match the committed example exactly.
- 2026-11-01 · hasan · WinForms cost, KeePass 2 in the #161 state · **pass** · main window 114
  elements in 819 ms (7.2 ms per element against #161's 19.8 with the dump's reader),
  `Add Entry` 40 in 363 ms, and 74 + 40 = 114 confirms the deduplication on a real owned dialog.
- 2026-11-01 · hasan · the blocking-provider path · **pass** · a Qt window whose GUI thread slept
  40 s: the *first* UIA read blocked, so no between-element check could ever fire; `snapshot`
  returned `-32002` after 2 251 ms of a 2 000 ms budget, twice in the same process, naming the
  likely cause, and the window snapshotted normally again (58 ms) after it thawed. Reproduction
  script `blocker.py` was in the session scratchpad; worth a `@pytest.mark.windows` test if the
  timer design is ever touched again.
- 2026-11-01 · hasan · end-to-end over JSON-RPC · **pass** · see Status above.
- **Still unverified: a second monitor at another scaling.** Every number above is from one
  120-DPI display, so `dpi` has only ever been 120 and no snapshot has had negative `bounds`.
  One check at the weekly Windows session would close it.

## Open issues
- **`minLength: 1` cannot say "not only spaces".** Both `snapshot.schema.json` and
  `element.schema.json` promise that a whitespace-only string is never stored and only enforce
  non-empty. The agent honours it (`model._blank`); a Java or TypeScript producer could write
  `"   "` and be valid. Named as a *valid* case in `examples/snapshot/cases.json` so the gap is
  visible, and raised under "Open, for the deciders" in the ADR. Recommendation: add
  `"pattern": "\\S"` to every string property in **both** schemas in one PR that bumps both to
  0.2, after #15 and #24 have landed against 0.1.
- **Settled: `pywinauto>=0.6.9` unconditional, and no `pywin32` line at all.** pywinauto is a
  pure-Python wheel (`py3-none-any`) and its own metadata already gates `comtypes` and `pywin32`
  to `sys_platform == "win32"`, so the macOS install keeps working and only Windows pulls the
  native parts. Declaring `pywin32` directly would have broken the macOS install outright —
  PyPI has only Windows wheels for it.
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
- **Two changes landed in galip's files**, both required by #12 and both written to his inbox:
  (1) `rpc.main()` now builds `UiaDesktop()`, as he offered; (2) `rpc.py`'s `__main__` block
  delegates to `ayna_agent.rpc.main`, because `python -m ayna_agent.rpc` otherwise loads the
  module twice and the two copies have two different `UiaUnavailable` classes — the backend's
  error then came out as `-32603` instead of `-32001`. Only the subprocess test caught it. See
  `learnings.md` 2026-11-01; the same trap waits for anything importing from a `__main__`
  module.
- **`setup()` deliberately does not raise** when UIA cannot run, against galip's "a failing
  `setup()` stops the server". `docs/agent-rpc.md` says a host without a backend answers -32001
  per call, and a server that refused to start would stop the client, the Spy and
  `test_cli_announces_its_port_and_answers` from running on macOS. The reason is recorded and
  every method raises `UiaUnavailable` with it. If galip prefers the hard failure it is three
  lines — but `rpc.main()` then needs a fallback to `UnavailableDesktop`.
- `test_cli_announces_its_port_and_answers` had to change: it asserted `-32001` from the
  placeholder backend, and now accepts either the window list (on a desktop) or -32001.
- A timeout leaks one daemon walk thread **by design**: the thread is inside a cross-process
  call that will not return. `UiaDesktop._abandoned` counts them and `close()` logs the count.
- The walk lives in `walk_from`, duck-typed on `UIAElementInfo`, so the order, the
  deduplication and the deadline are testable with fakes on macOS. That split is what
  `agent/AGENTS.md` asks for, and it is where to add cases.

## Outcome (fill when the issue closes)
Delivered: `schemas/snapshot.schema.json` 0.1 with a real example and 39 named cases;
`recognition/snapshot.py` (the document, a canonical text, the round trip) and
`recognition/uia.py` (the UI Automation backend, wired into `rpc.main()`); ADR
`2026-11-01-snapshot-schema-v0` (Proposed); the `snapshot` success example in
`docs/agent-rpc.md`; 95 new tests, whole agent suite 280 green. All three acceptance criteria
met, the first one measured at 28–32 ms against the 2 s bound. PR: _to add_.
