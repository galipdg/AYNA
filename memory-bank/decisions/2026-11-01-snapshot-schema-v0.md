# Snapshot schema v0: a flat pre-order tree, one window, and no partial document

- Date: 2026-11-01
- Status: Accepted (Hasan proposed it; Ömerfaruk approved PR #180; Galip approved on #180, 2026-11-02)
- Deciders: Galip, Ömerfaruk, Hasan
- Issues: #12 · consumed by #15, #24, #25, #73, #149 · evidence from #6, #9, #161 · extends
  `2026-10-31-element-descriptor-v0`

## Context
`schemas/snapshot.schema.json` is the one document that carries a window's whole element tree
between all three components: the agent captures it (#12), the server imports it as Window and
Element nodes under an AppVersion (#15), the Spy shows it as a tree with a property panel (#24,
#25), and a healing proposal travels with it so that its candidates can be read back (#149,
#73). Four facts shaped it.

- **Three consumers were already waiting on the shape, not the code** (ömer on #12, 2026-10-31
  and again 2026-11-01): #15 is due this week and the G0 demo is 9 November. That is why the
  schema and an example landed before the UI Automation backend rather than after it.
- **The descriptor is settled** (`element.schema.json`, #11): 17 properties, three of them
  computed by rules healing has to reproduce (#43). A snapshot adds nothing to an element; it
  only says where each one sits.
- **A UIA walk can be pathologically slow** (#161): the same WinForms pilot window walks in
  2.26 s normally and took 230 s with a modal message box open, 2.71 s *per element*, matching
  the 278.5 s of the #6 dump to within 3 %. So a snapshot needs a deadline and an outcome for
  "did not finish", and it needs to record its own cost.
- **An owned dialog is both a top-level window and a child of its owner** (#6, #170 review):
  KeePass's `Add Entry` is a child of the main form's ToolBar, so a naive walk reports 154
  "elements" for a tree of 114.

## Decision

### 1. One document per window, elements as a flat list in pre-order
`schemas/snapshot.schema.json` (`urn:ayna:schema:snapshot`, version `0.1`), built by
`agent/ayna_agent/recognition/snapshot.py`. The document is
`{version, snapshotId, capture, app, window, elements}`, and `elements` is a **flat array**,
each entry `{id, parentId, element}`:

- **Flat, not nested.** The #6 dumps and `model.describe_tree` already work on a flat list with
  parent ids, a healing candidate has to name one element by id (#149), and a flat list imports
  and streams without recursion. Nesting would buy nothing and cost every consumer a tree walk.
- **Pre-order, the window's own root element first, a parent always before its children.** One
  pass then builds the tree, which is exactly what #15's import and #24's tree do. The schema
  cannot say this, so `snapshot.loads` refuses a document that breaks it.
- **`id` is `e<position>`** in that order and **opaque**: stable inside one document, never
  parsed, ordered or compared across documents. Same `opaqueId` definition as the healing
  proposal, so `candidates[].elementId` resolves against `elements[].id`.
- **Exactly one root**, because a snapshot is one window. A dialog that is also a child of its
  owner appears once, as a descendant: the walk deduplicates by window handle and orders its
  roots owner-first (#6, #161).

### 2. The element is the descriptor, duplicated on purpose
`$defs/element` repeats `element.schema.json#/$defs/element` property for property instead of
`$ref`-ing it. A cross-file `$ref` to a `urn:` id needs a resolver registry in every one of
Java, TypeScript and Python, and the healing proposal already set the precedent with its own
`scoredElement`. `agent/tests/test_snapshot.py` compares the two property maps, constraints
included, so they cannot drift; only the descriptions differ, and `element.schema.json` stays
the normative place for the reasons behind each property.

### 3. `capture`: every snapshot carries what it cost
`startedAt` (ISO 8601 **with offset**), `durationMs`, `budgetMs`, `elementCount`, `readErrors`,
`agentVersion`, `featureVersion`. This is #161's one recommendation that would have made that
whole investigation unnecessary: a slow capture must be attributable from the document itself.
`startedAt` is the healing proposal's `snapshotAt`, so a screenshot taken before the walk (#54)
is older by at most `durationMs`. `featureVersion` (`features-v0`) says how the computed
properties were derived, because healing recomputes them from the stored snapshot (#43) and a
snapshot derived by another rule set is not comparable.

### 4. The default budget is 5 000 ms, and an incomplete walk is **not** a document
Measured in #161 (`eval/spikes/uia-walk-cost.md`): 2.2× the slowest full walk on a pilot window
and room for ~330 WinForms elements at 15.3 ms each, against the 114 that window has. Not
NFR-02's 2 s, which is scoped to the sample app (Qt, ~4.3 ms per element without the pattern
probes) and which a 200-element WinForms window would breach through no fault of the agent.

A walk that passes its budget raises `SnapshotTimeout` → JSON-RPC `-32002` and returns **no
document at all**, so `durationMs < budgetMs` holds in every stored snapshot. The same applies
to any element or depth guard: there is one failure state, never a partial tree. The reason is
TBD-5's third category, RS 0.6 *search incomplete* (FR-35), which never starts healing (FR-29):
candidates ranked from a partial tree give a confident but unfounded proposal.

The budget is a **deadline on a timer**, not a per-element timeout. Under a modal message box a
single container blocked for 72 s inside one `FindAll` (#161), and code inside a blocking
cross-process call cannot check a clock; the p99 element is also 10× the median, so a
per-element limit would cut exactly the tab containers that matter.

### 5. `app` and `window` say what was read, not what it is called
`app` is `{exeName, fileVersion}` — the exe's file name and version resource, both optional. The
server's `Application.name` and `AppVersion.version` are chosen by a person at import (#15): one
exe serves many named applications, and a file version is not the version a tester writes on a
release. The full exe path is left out because it names the user (#6). `window` carries the
window-manager identity (`handle`, `processId` — both session-scoped and never matched across
runs) plus `title`, `className`, `bounds` and `dpi`; the window's UIA properties are
`elements[0].element`, not repeated.

### 6. A canonical text, so load → save gives the same file
`snapshot.dumps` writes a fixed key order, two-space indent, LF on every OS, UTF-8 unescaped
(Turkish labels stay readable), one trailing newline. `dumps(loads(text)) == text` for every
document the module accepts, including one whose keys arrived in another order — the round trip
is defined on the canonical form, not on whatever order a file happened to be written in. That
is #12's third acceptance criterion.

## Alternatives considered
- **Nested children instead of parent ids.** Rejected: a healing candidate needs an addressable
  id, the #6 dumps and `describe_tree` are flat already, and every consumer would gain a
  recursion it does not need.
- **`$ref` into `element.schema.json`.** Rejected for now: resolving a `urn:` `$ref` needs a
  registry in three languages. Revisit if the schemas ever get an `$id` base URL and a bundler.
- **A partial document with `truncated: true`.** Rejected: it is exactly the input FR-29
  forbids healing to use, and a flag that must be checked by three components in two languages
  will be missed once. One failure state is cheaper to get right.
- **Budget 2 s, to match NFR-02.** Rejected: NFR-02 is a property of the sample app (#143), and
  a WinForms pilot window of 200 elements would fail a 2 s walk while behaving perfectly.
- **`elementCount` left out as derivable.** Kept deliberately: a log line or a list of snapshots
  must report the size without carrying the tree. `loads` checks it against the array, so the
  redundancy cannot rot.

## Consequences
- #15 can import against a fixed shape today: one pass over `elements`, `Window` from `window` +
  `snapshotId`, `Element` per entry, `CONTAINS` from `parentId`. Importing the same `snapshotId`
  twice must leave the graph unchanged (FR-04).
- #24 / #25 can build the Spy tree in one pass and show `capture` in the panel.
- #149: `healingProposal.snapshotId` is this document's `snapshotId` and every candidate's
  `elementId` is one of its `elements[].id`. `snapshotAt` is `capture.startedAt`.
- #43 must derive `parentPath`, `siblingIndex`, `nearestLabel` and `dpi` by the rules of the
  element-descriptor ADR, and bump `FEATURE_VERSION` with any change to them. The constant
  currently lives in `recognition/snapshot.py`; it moves to `heal/features.py` when #43 lands,
  and there must only ever be one.
- A client that wants a bigger budget passes `timeoutMs` (1–600 000) to `snapshot`; the document
  records which budget applied.

## Open, for the deciders
**`minLength: 1` cannot say "not only spaces".** Both this schema and `element.schema.json`
state that a whitespace-only string is never stored, and both only enforce a non-empty one. The
agent honours the rule (`ayna_agent.model._blank`), but a Java or TypeScript producer could
write `"   "` and be valid. The case is in `schemas/examples/snapshot/cases.json` under *valid*,
named for what it is. Closing it means adding `"pattern": "\\S"` to every string property in
**both** schemas, which is a change to a frozen contract and so belongs in this decision rather
than in a quiet commit. Hasan's recommendation: add it, in one PR that bumps both schemas to
0.2, after #15 and #24 have landed against 0.1 — the gap is a producer bug today, not a
consumer risk.
