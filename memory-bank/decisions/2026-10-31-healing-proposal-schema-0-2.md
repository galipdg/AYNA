# Healing proposal schema 0.2: per-element DPI, feature versions, and the #151 review follow-ups

- Date: 2026-10-31
- Status: Proposed — accepted when Galip, Ömerfaruk and Hasan approve the PR
- Deciders: Galip (proposal, agent RPC, scorer, features #43), Ömerfaruk (client, server, graph), Hasan (recognition, playback, CLI runner)
- Issue: #149 (scorer follow-up PR #166; consumers #73, #74, #75, #11, #12, #54, #63, #103)
- Extends: [Healing proposal transport](2026-10-28-healing-proposal-transport.md), which stays Accepted and unchanged. Where the two differ, this ADR applies once accepted.

## Context
- **`dpi`.** PR #166 (scorer follow-up to #49) lets each scored element carry `dpi`, the DPI of its window (`GetDpiForWindow`; 96 = 100 % scaling). Location and area are compared in device-independent pixels (DIP); `bounds` stay physical everywhere else. Schema 0.1's `$defs/scoredElement` is the scorer's element with `additionalProperties: false` and no `dpi`, so a proposal that echoes the elements as scored fails validation as soon as #12 sends `dpi` ([omer, #166 review, point 2](https://github.com/galipdg/AYNA/pull/166#pullrequestreview-5722259973)). The same point: the schema's `bounds` says "screen pixels", while `docs/agent-rpc.md` says physical pixels in virtual-desktop coordinates.
- **Feature version.** `nearestLabel`, `parentPath` and `siblingIndex` are derived by the agent, and the derivation will change at least once: in the #6 dumps `LabeledBy` is set on 5 of 219 interactive elements, on the row container rather than the control, so #11 derives the nearest label geometrically. The target's properties were derived by the agent that recorded the element; the candidates' by the agent running now. Nothing in a 0.1 proposal says which derivation produced its numbers, yet #103 (calibration) and RQ5 replay stored proposals. Hasan asked for "a `featureVersion` (or `extractorId` + version) next to `scorer.id`" ([#151 review, §2](https://github.com/galipdg/AYNA/pull/151#pullrequestreview-5700948852)).
- **Open review points.** Other asks from the #151 reviews were not folded in before it merged: screenshot timing and coordinate space, no redelivery, 0-based `stepIndex`, `notRun` writes and the silent gap while candidates are collected (Hasan, §1, §3–§6); "the agent dies with the client", repeats with another body and outbox items per server (omer, [points 1–4](https://github.com/galipdg/AYNA/pull/151#pullrequestreview-5698114259)); notifications have no `id` (Hasan, [comment](https://github.com/galipdg/AYNA/pull/151#issuecomment-6504420628)).
- **No stored proposals.** #73 (producer) and #74 (store) are not built, so changing the schema now costs only this ADR. Contracts freeze at G1 (#52, 7 Dec).

## Options considered

**1. Where `dpi` goes**
- a. *An optional integer `dpi` on `scoredElement`*, with #166's key and meaning. + The proposal stays "the elements exactly as scored"; the target's value comes from the stored Element (omer, #166 review, point 3). − None found.
- b. *One `dpi` per proposal.* − The target and the candidates may come from machines with different scaling (a pilot recording, a CI run), which is why #166 made it per element.

**2. The form of the feature version**
- a. *One string, `featureVersion`*, name and version together (`"features-v0"`), like `scorer.id` (`"similo-v0"`). + Smallest: one value per fact.
- b. *`extractorId` and `extractorVersion`.* − Two fields for one fact: there is one extractor (the agent's), consumers only compare it for equality, and `scorer.id` already packs name and version into one string.
- c. *A key inside every scored element.* − Puts a value the scorer never reads into "the properties as scored" and repeats it on every candidate.

**3. Where the feature version goes**
- a. *Only `scorer.featureVersion`*, for the agent that derived the candidates. − Cannot show Hasan's case: a target recorded by an older derivation.
- b. *Also `target.featureVersion`*, the version that derived the target's stored properties, when known. + A replay sees the mismatch from the document alone, also offline. − The server must keep the version on Element, next to `dpi`.

**4. Required or optional**
- a. *Required.* + A producer cannot forget it. − 0.2 would stop being a superset of 0.1, and the target's version cannot be known for elements stored before the server keeps it.
- b. *Optional, with a producer rule:* the agent always writes `scorer.featureVersion`, which #73's contract test enforces because the shared examples carry it. + 0.2 is a superset of 0.1, so relabelling is the whole migration.

## Decision
**1a, 2a, 3b, 4b**, and the follow-ups below.

### Schema 0.2
| Change | Where | Type | Meaning |
|---|---|---|---|
| `dpi` | `$defs/scoredElement`: the target's `properties` and every candidate's `element` | integer ≥ 1, optional | DPI of the element's window (`GetDpiForWindow`); 96 = 100 %. Key and meaning as in `agent/ayna_agent/heal/scorer.py` (#166). Not a scored property: never a key of `weights`, `contributions` or `similarities`. Left out when unknown; how the scorer treats a `dpi` known on one side only is the scorer's rule (both #166 reviews ask to change it), not the schema's. |
| `featureVersion` | `scorer` | string, `^[a-z][a-z0-9-]*$`, ≤ 50, optional | Feature version of the agent that derived the candidates' properties: how `nearestLabel`, `parentPath`, `siblingIndex`, `windowTitle` and `dpi` are computed from UI Automation. The agent always writes it. |
| `featureVersion` | `target` | same, optional | The version that derived the target's stored properties when the element was recorded. Left out when unknown, never `null`. |
| `bounds` (description only) | `$defs/scoredElement` | unchanged | Physical pixels, virtual-desktop coordinates, as UI Automation reports them to the per-monitor-v2 DPI aware agent. Never scaled by `dpi`. |
| `version` | root | const `"0.2"` | Each release accepts only its own label. |
| `versionedId` | `$defs` | — | Shared by `scorer.id` and both `featureVersion`s; `scorer.id` accepts exactly what it accepted before. |

Rules:
- The agent has one constant, `FEATURE_VERSION`, next to the code that builds a scored element from the descriptor (#43, `agent/ayna_agent/heal/features.py`); its first value is `"features-v0"`. A PR that changes how one of those properties is derived, in #11 (descriptor) or #43 (graph features), bumps it in the same PR.
- `scorer.id` is bumped when a similarity rule or a weight changes after the first proposal is stored. #166's DIP rule lands before any proposal exists, so the first id #73 writes stays `similo-v0` and means the DIP version.
- Whoever replays or compares stored proposals (#103, RQ5, the decision log #63) groups them by `scorer.id` and `scorer.featureVersion`, and treats a proposal whose `target.featureVersion` differs from `scorer.featureVersion` as not comparable. A missing feature version means "unknown", never "the same".

### Follow-ups to the transport ADR (#151 reviews)
The transport ADR's decisions (1a, 2a, 3a, 4b, 5a) stand. These points refine it.

1. **No redelivery; `aborted` makes the gap visible** (Hasan §4). `run.stepResult` is a notification: nothing acknowledges it and the agent never sends it again. A crash between the client receiving a result and appending it to the outbox loses that result, which is why such a run is finished as `aborted`: the gap is visible, not silent. The client appends a result to the outbox **before** it shows it (the transport ADR's step 4 listed showing first).
2. **Notifications carry no `id`** (Hasan, comment). Since v0.1, replies come in any order. The client recognises an agent notification by the missing `id` and routes it by `method`, never by its position among replies.
3. **Screenshot of a `repairProposed` step** (Hasan §1 and §6). This replaces "taken at the same moment as its snapshot". The agent takes the screenshot immediately before the snapshot walk starts, because a walk can take minutes (278.5 s for one KeePass 2 window in #6). The step result records both times (`screenshotAt`, `snapshotAt`; the names are #54's and #40's to settle), so the approval screen can say how much older the image is than the geometry. The crop rectangle and the candidates' `bounds` are in the same space, physical pixels in virtual-desktop coordinates, which holds because the agent is per-monitor-v2 DPI aware (#12). `dpi` never rescales `bounds` for drawing. The image travels as #54 and #51 decide (omer prefers a separate binary upload, `PUT …/results/{stepIndex}/screenshot`); the JSON payload does not change.
4. **The silent gap while candidates are collected** (Hasan §1). v0.2 adds no progress message. Between the previous step's result and a `repairProposed` result the client hears nothing, possibly for minutes; it shows the step after the last result as running, with the elapsed time (#44). A progress notification can come later as a minor addition, because clients ignore notification methods they do not know.
5. **`stepIndex` is 0-based** (Hasan §5): a position in the run, deliberately unlike the 1-based row numbers a tester sees (`row.index` in step schema 0.2, PR #150). A screen adds 1 when it shows a step number.
6. **"The agent dies with the client" now holds** (omer, point 1). Since #135 the agent exits on stdin EOF, which the OS causes when the client quits or crashes (`docs/agent-rpc.md`, "Starting the agent").
7. **A repeat with another body** (omer, point 2). `PUT /api/runs/{runId}/results/{stepIndex}` answers 200 only for an identical repeat (compared by a hash of the canonical JSON). A different body for the same `(runId, stepIndex)` answers 409, and the client moves the item to the dead-letter file. This replaces "first write wins, a repeat returns 200".
8. **Outbox items belong to one server** (omer, point 3). Each item records the server URL it was created for, and the forwarder sends it only there, also after the user changes the server URL (#32).
9. **`notRun` writes** (Hasan §3). Per-step writes stay for v1: one code path and one idempotency key. If #61's first CI runs show the cost, #51 may add a bulk write that takes an array of the same documents; that is additive and changes no payload. Notifications stay one per step.

## Compatibility
- 0.2 is a superset of 0.1: every new key is optional and nothing is removed or narrowed, so a 0.1 document becomes a valid 0.2 document by changing `version` (`ai/tests/test_healing_proposal_schema.py` checks it on every example).
- No 0.1 proposal exists anywhere (#73 and #74 are not built), so nothing needs migrating and the server accepts only `"0.2"`.
- The example numbers are unchanged. The examples now carry `dpi: 96`, which makes the DIP conversion the identity; every score, contribution and similarity was recomputed with the scorer on `main` and on PR #166's branch, and both reproduce the stored strings. `parentPath` in the examples now uses programmatic ControlType names (`Window/Group`), #166's input contract; all elements share it, so its similarity stays 1. `cli-run-without-server.json` shows a target without `dpi` or feature version.
- Agent RPC: only the document inside `healingProposal` changes; `rpcVersion` still becomes `"0.2"` when #40 and #73 ship the notification.

## Consequences
**Hasan (recognition, playback, CLI runner)**
- #11, #12: descriptors and snapshot elements carry `dpi` (int, `GetDpiForWindow` of the top-level window); a change to how #11 derives a scored property (the geometric nearest label) bumps `FEATURE_VERSION`.
- #73: write `dpi` as scored, `scorer.featureVersion` always, and `target.featureVersion` when the run request's target has it; take the screenshot before the snapshot walk.
- #54: `screenshotAt` and `snapshotAt`; the crop rectangle in physical virtual-desktop pixels.
- #63: decision log records keep `scorer.id` and both feature versions (also asked in Hasan's #144 review, §4).
- #61: per-step `notRun` writes in v1.

**Ömerfaruk (client, server, graph)**
- #25 and `docs/graph-model.md`: keep `dpi` (int) and `featureVersion` (string) on Element next to `bounds`, as recorded; the run request's `targets` (#40) passes both back to the agent.
- #74: validate against 0.2, accept only `"0.2"`, store the document unchanged.
- #51: 409 for a repeat with another body; a bulk write only if #61 needs it.
- #44: append before showing; each outbox item names its server; show the running step with its elapsed time.
- #75: draw `bounds` as physical pixels on the screenshot; show the image's age from the two timestamps.

**Galip (scorer, features, documents)**
- #43: `FEATURE_VERSION = "features-v0"` and the bump rule above.
- #166: the one-sided `dpi` rule stays the scorer's; it needs no schema change.
- #103: replays group by `scorer.id` and `scorer.featureVersion`.
- This PR: schema, examples, tests, `docs/agent-rpc.md` "Proposed (#149)", SDD AI-5.2 and AI-5.5.

**Freeze (#52)**
- Once accepted, `schemas/healing-proposal.schema.json` 0.2 replaces 0.1 in the transport ADR's freeze list.
