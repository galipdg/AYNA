# #149 Healing proposal transport: agent → client/CLI → server

- Issue: https://github.com/galipdg/AYNA/issues/149
- Owner: galip · Branches: `galip/149-proposal-transport` (PR #151, merged); `galip/149-proposal-schema-0-2` (schema 0.2 and the #151 review follow-ups)
- Started: 2026-10-28 · Last update: 2026-10-31

## Approach
A contract decision, so the deliverable is an ADR with status Proposed plus the galip-owned contract text; nothing is implemented until all three approve. ADR: `memory-bank/decisions/2026-10-28-healing-proposal-transport.md`. Agent side: `docs/agent-rpc.md`, section "Proposed (#149)". Payload: `schemas/healing-proposal.schema.json` (version 0.1, proposed) with examples in `schemas/examples/healing-proposal/` and checks in `ai/tests/test_healing_proposal_schema.py`. The REST endpoints are proposed in the ADR only; omer owns the REST contract (#51, #74).

In one line: the proposal rides inside the failing step's `run.stepResult` notification (agent → client), which the client forwards unchanged through a durable outbox to `PUT /api/runs/{runId}/results/{stepIndex}`; the CLI runner writes the same document to the same endpoint; numbers are exact fractions as strings.

## Decisions (small, local to this task)
- 2026-10-28 — Branch stacked on `galip/16-agent-rpc` because #135 owns `docs/agent-rpc.md`; the PR targets `main` and says to merge after #135.
- 2026-10-28 — Proposal embedded in the step result, not a separate `heal.proposed` message or `POST /api/healing/proposals`: one fact, one write, no half-delivered state, and the client forwards it with no healing-specific code. Read and decision endpoints stay under `/api/healing/proposals` (#74).
- 2026-10-28 — The failing step's result carries the window snapshot (#12 document) so candidates become ordinary Element nodes through the normal snapshot import; the proposal itself carries only `snapshotId` + snapshot element ids, so its schema does not depend on #12's unfinished shape.
- 2026-10-28 — Candidates and target carry the properties exactly as scored, plus the weights: the proposal is self-checking (each contribution = wᵢ·simᵢ / Σw over the compared properties), independent of the #11 → scorer adapter.
- 2026-10-28 — Exact fractions as strings (`str(Fraction)`: `"151/192"`, `"1"`, `"0"`), no floats on the wire: one value per quantity, the sum is exact in every language; screens convert to double for drawing.
- 2026-10-28 — `createdAt` left out of the proposal: the step result carries timing (#40) and the server records decision times; fewer fields to freeze.
- 2026-10-28 — Target id named `serverElementId` (graph `Element.id`), candidate id `elementId` (id inside `snapshotId`) so the two id spaces cannot be confused.
- 2026-10-28 — `uuid` and `logicalName` copied from `step.schema.json` (#134, not merged) instead of a cross-schema `$ref`, so each schema validates on its own.
- 2026-10-28 — Schema tests in `ai/tests/` like the step schema's (#134 precedent): the `ai` CI job is where `jsonschema` lives. No new dependency: the schema half uses `pytest.importorskip("jsonschema")` and runs in CI once #134 is merged; the arithmetic half needs only the standard library and always runs.
- 2026-10-28 — Example numbers produced by the real scorer (`origin/galip/49-healing-scorer`, `rank(..., k=3)` on a renamed login button), not typed by hand.
- 2026-10-28 — No change to `agent/ayna_agent/rpc.py`: there is no playback yet to emit notifications, so a hook now would be untested scaffolding. `RPC_VERSION` stays 0.1 until #40/#73 ship the messages.
- 2026-10-28 — TBD-10 (CLI credentials): recommend an API token for a CI service account in `AYNA_SERVER_TOKEN`; final choice in #60/#61.
- 2026-10-31 — Schema 0.2 work extends this note instead of a new `149-proposal-schema-0-2.md`: same issue, same contract, and one note per issue keeps the history in one place.
- 2026-10-31 — New ADR `2026-10-31-healing-proposal-schema-0-2.md` (Proposed) extends the Accepted transport ADR, which is never edited.
- 2026-10-31 — Feature version as one string `featureVersion` (`"features-v0"`), not `extractorId` + version: one extractor, compared only for equality, same form as `scorer.id`. Placed in `scorer` (candidates, the agent running now) and in `target` (recorded element, when known), because Hasan's case is a target derived by an older agent.
- 2026-10-31 — Every 0.2 key optional so that 0.2 is a superset of 0.1 (relabelling is the whole migration). The agent's duty to write `scorer.featureVersion` is enforced by #73's contract test against the examples, which carry it. Required was the alternative; reviewers may flip it.
- 2026-10-31 — Examples get `dpi: 96`, which makes #166's DIP conversion the identity; numbers recomputed with the scorer on `main` and on `origin/galip/49-dpi-location` (PR #166): both reproduce every stored string. The one-sided-`dpi` case is left out of the cases because its numbers depend on the scorer rule both #166 reviews ask to change.
- 2026-10-31 — Example `parentPath` changed to programmatic ControlType names (`Window/Group`), #166's input contract; all elements share it, so similarity stays 1.
- 2026-10-31 — No progress notification in v0.2 (Hasan's "say which it is"): the client shows the running step with elapsed time; a progress method can be added later because clients ignore unknown notifications.
- 2026-10-31 — Recorded omer's 409-on-different-body and outbox-per-server, and per-step `notRun` writes for v1, in the new ADR, so the transport ADR's readers find them next to the schema change.

## Status
- [x] Branch, task note, board → In progress
- [x] ADR (Proposed) + README line
- [x] `docs/agent-rpc.md` "Proposed (#149)" section
- [x] Schema, examples, tests
- [x] PR https://github.com/galipdg/AYNA/pull/151 (`Refs #149`, stacked on #135) opened 2026-10-28; reviews requested from HasanBerk18 and omerfaruksaribal; asks in their inboxes. Locally: 56 ai tests pass with jsonschema, 17 pass + 38 skip without; ruff clean
- [x] All three approved; transport ADR Accepted; PR #151 merged
- [ ] After approval: comment on #73 and #74 linking the ADR (AC 3); omer names the endpoint in the #74 REST contract (AC 2)
- [x] 2026-10-31 schema 0.2 on `galip/149-proposal-schema-0-2`: `dpi`, `scorer.featureVersion`, `target.featureVersion`, `bounds` wording, version `"0.2"`; examples and cases; tests (69 pass); ADR 0.2 (Proposed) + README line; `docs/agent-rpc.md` "Proposed (#149)" review follow-ups; SDD AI-5.2 latency wording (#144 review) and AI-5.5 payload; `schemas/README.md` section
- [ ] PR for schema 0.2 reviewed by all three → ADR 0.2 Accepted (and its README line) in that PR
- Next step: answer the reviews on the schema 0.2 PR; once accepted, comment on #73 and #74 with both ADR links.

## Manual checks
- None: documentation and schema only; nothing runs on Windows.

## Open issues
- After approval, galip updates: SDD AI-5.5 "Storage" and AI-9 rows 7 and 8 (omer's #144 review, point 3; the AI-5.5 payload line is done on the 0.2 branch), RS TBD-6 and TBD-10 and the FR-23 exit code when results cannot be delivered (PR #143), and adds `SCORER_ID = "similo-v0"` to `heal/scorer.py` (#49) when #73 wires it in.
- #43 (galip): add `FEATURE_VERSION = "features-v0"` in `heal/features.py` and the bump rule of the 0.2 ADR.
- Hasan's #144 review §4 asks the decision log (#63) to record whether the snapshot was complete (budget, #12); not part of the proposal schema, left to #63/#12.
- `schemas/AGENTS.md` lists only the three original schemas; after #134 merges, its Layout and Commands lines need `healing-proposal.schema.json` and its test (ask first: it is an AGENTS.md).
- Several pending proposals for the same object and version (two failed runs before a review): #74 should decide whether approving one closes the others.

## Handoff
- The ADR's REST names (`PUT /api/runs/{runId}/results/{stepIndex}`, `/api/healing/proposals/...`) are proposals for omer, not a contract; `docs/api/openapi.yaml` is generated from server code.
- Regenerate the example numbers with the scorer if #49 changes before merge: `python make_example.py` lived in the session scratchpad; the inputs are the `target` and `element` objects of `login-button-renamed.json`.
- To check the examples against a scorer: load each example's `target.properties` and candidates' `element`, call `heal.scorer.score(target, element)` and compare `str()` of score, contributions and similarities with the stored strings (done 2026-10-31 for `main` and PR #166).

## Outcome (fill when the issue closes)
