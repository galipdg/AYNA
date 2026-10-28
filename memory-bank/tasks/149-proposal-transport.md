# #149 Healing proposal transport: agent → client/CLI → server

- Issue: https://github.com/galipdg/AYNA/issues/149
- Owner: galip · Branch: `galip/149-proposal-transport` (stacked on `galip/16-agent-rpc`, PR #135)
- Started: 2026-10-28 · Last update: 2026-10-28

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

## Status
- [x] Branch, task note, board → In progress
- [x] ADR (Proposed) + README line
- [x] `docs/agent-rpc.md` "Proposed (#149)" section
- [x] Schema, examples, tests
- [x] PR https://github.com/galipdg/AYNA/pull/151 (`Refs #149`, stacked on #135) opened 2026-10-28; reviews requested from HasanBerk18 and omerfaruksaribal; asks in their inboxes. Locally: 56 ai tests pass with jsonschema, 17 pass + 38 skip without; ruff clean
- [ ] All three approve → ADR Accepted (and its README line) in the same PR
- [ ] After approval: comment on #73 and #74 linking the ADR (AC 3); omer names the endpoint in the #74 REST contract (AC 2)
- Next step: address review comments on the PR.

## Manual checks
- None: documentation and schema only; nothing runs on Windows.

## Open issues
- After approval, galip updates: SDD AI-5.5 and AI-9 rows 7 and 8 (PR #144), RS TBD-6 and TBD-10 and the FR-23 exit code when results cannot be delivered (PR #143), and adds `SCORER_ID = "similo-v0"` to `heal/scorer.py` (#49) when #73 wires it in.
- `schemas/AGENTS.md` lists only the three original schemas; after #134 merges, its Layout and Commands lines need `healing-proposal.schema.json` and its test (ask first: it is an AGENTS.md).
- Several pending proposals for the same object and version (two failed runs before a review): #74 should decide whether approving one closes the others.

## Handoff
- The ADR's REST names (`PUT /api/runs/{runId}/results/{stepIndex}`, `/api/healing/proposals/...`) are proposals for omer, not a contract; `docs/api/openapi.yaml` is generated from server code.
- Regenerate the example numbers with the scorer if #49 changes before merge: `python make_example.py` lived in the session scratchpad; the inputs are the `target` and `element` objects of `login-button-renamed.json`.

## Outcome (fill when the issue closes)
