# #15 Snapshot import API

- Issue: https://github.com/galipdg/AYNA/issues/15
- Owner: omer · Branch: `omer/15-snapshot-import`
- Started: 2026-11-03 · Last update: 2026-11-03

## Approach
`POST /api/apps/{appId}/versions/{versionId}/snapshots`, body = a snapshot 0.1 document (#12, ADR `2026-11-01-snapshot-schema-v0`). Package `server/src/main/java/com/ayna/server/snapshots/`:
- `SnapshotSchema`: `schemas/snapshot.schema.json` via the shared `schema/SchemaFile` (extracted from `StepSchema`, same networknt setup) plus the rules JSON Schema cannot say: unique ids, one root first, strict pre-order (ancestor stack), `capture.elementCount` = `elements.length`, `startedAt` parseable by `OffsetDateTime`.
- `SnapshotService.importInto(tx, versionId, doc)`: public so #51's `repairProposed` write can import in its own transaction (healing-transport ADR). Three Cypher statements: Window + Elements (UNWIND), Window→root, parent→child links.

## Decisions (small, local to this task)
- 2026-11-03 — Every snapshot entry becomes an Element, the window's own root (`e0`) too; `(Window)-[:CONTAINS]->(e0)` only. Trial snapshot = 14 Elements = `capture.elementCount`, and healing candidate ids map one-to-one (user approved).
- 2026-11-03 — Idempotency by `snapshotId`: first import 201; same id into the same version 200 with the stored window and no write, even if the body differs (the id is the identity, FR-04); same id under another version 409 (user approved).
- 2026-11-03 — Check in the write transaction, no uniqueness constraint (as #128): two concurrent imports of one new snapshot id can both succeed. A constraint would be a migration + ADR (user approved).
- 2026-11-03 — Window keeps `snapshotId`, `name` (← `window.title`), `className`, `capturedAt` (Neo4j datetime from `capture.startedAt`), `featureVersion`, `exeName`, `fileVersion`; not `handle`/`processId` (session-scoped) (user approved). Element keeps every descriptor property + `snapshotId` + `snapshotElementId` (agent's `e<n>` id); `bounds` as a long list.
- 2026-11-03 — No `Location` header: there is no GET for a snapshot yet; the response body carries `windowId`.
- 2026-11-03 — `docs/graph-model.md` Window/Element rows and the `CONTAINS` samples updated to match (property descriptions only; no migration).

## Status
- [x] schema validation + tree rules, `SnapshotSchemaTest` (10, incl. every case in `schemas/examples/snapshot/cases.json`)
- [x] import endpoint, `SnapshotIntegrationTest` (6); `./mvnw test` 56/56 green 2026-11-03; `openapi.yaml` regenerated
- [x] `server/Dockerfile` + `.dockerignore` copy `snapshot.schema.json`; image built and checked against a throwaway Neo4j: 201 → 200 → 400
- [x] pushed; PR #182 open (`Closes #15`) on 2026-11-03, review requested from hasan (schema reading) and galip (`importInto` for #51/#74)
- [x] 2026-11-03: merged `origin/main` (#179, accounts). Import now follows the #60 rule: `createdBy`/`createdAt` on Window, `UserRef createdBy` + `createdAt` in the response; `importInto(..., userId)`. `openapi.yaml` regenerated (conflict resolved by regenerating); `./mvnw test` 70/70
- Next step: wait for #182 reviews (hasan, galip); answer review points on this branch

## Manual checks
- None needed: covered by the integration test; the Docker image was checked by hand on 2026-11-03 (omer's agent, curl).

## Open issues
- `LABELLED_BY` is not written: the snapshot carries `nearestLabel` as text, not an element id. If #42/#43 need the edge, the agent would have to name the label element (snapshot 0.2).
- Race on concurrent imports of one new snapshot id (see Decisions). A V000x unique constraint on `Window.snapshotId` would fix it (ADR).
- Clients that need the tree back (#24 Spy from the server, #25) will need a GET; not in #15's scope.

## Handoff
- Response: `{windowId, snapshotId, appVersionId, name, className, elementCount, createdBy, createdAt}` (the first importer; a repeat import returns the same); `name`/`className` may be absent when the agent could not read them.
- Adding another shared schema to the server needs three edits: `pom.xml` resources, `server/Dockerfile` COPY and `server/Dockerfile.dockerignore`.

## Outcome (fill when the issue closes)
