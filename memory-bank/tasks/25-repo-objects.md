# #25 Add element to the object repository

- Issue: https://github.com/galipdg/AYNA/issues/25
- Owner: omer · Branch: `omer/25-repo-objects` (stacked on `omer/15-snapshot-import` until PR #182 merges; the client part also needs `omer/24-object-spy`)
- Started: 2026-11-03 · Last update: 2026-11-03

## Approach
Server: `POST /api/apps/{appId}/repo-objects`, body `{name, snapshotId, snapshotElementId, primary, fallback}` (`server/.../repository/`). The client first imports the picked element's snapshot (#15, idempotent), then posts the object; the server finds the Element by `(snapshotId, snapshotElementId)`, checks the snapshot is in this application, and writes `(Application)-[:HAS_OBJECT]->(RepoObject)-[:RESOLVES_TO {version}]->(Element)` in one transaction.
Client: "Add to repository" under the Spy's property panel (#24) opens `renderer/src/AddToRepository.tsx`: logical name, application version (list + "add version" inline), and one row per identifying property with an editable value and a Primary / Fallback / Not used choice. Suggestions come from `shared/repository.ts` `suggestUses`. Main process `main/repository.ts` imports the snapshot under the version, then creates the object.

## Decisions (small, local to this task)
- 2026-11-03 — App-scoped path `/api/apps/{appId}/repo-objects` instead of the issue's `/api/repo-objects`: matches the tests API (user approved).
- 2026-11-03 — `primary` / `fallback` stored as JSON strings (property → value, insertion order = best first), as `Step.checkpoint`; they are always read and written whole (user approved).
- 2026-11-03 — Allowed keys = the element descriptor's properties (`snapshot.schema.json#/$defs/element`) minus `NEVER_MATCH` (`bounds`, `dpi`, `nativeWindowHandle`, `frameworkId`, `enabled`, `offscreen`) and `nearestLabelSource`. Read from the schema, so win32 properties (#23) become allowed when the schema gets them. Values are type-checked against the schema only; they may differ from the Element's values, since the user may edit them.
- 2026-11-03 — `bounds` and `dpi` are **not** copied onto RepoObject (the design preview had them): they stay on the resolved Element (#15 stores them), which is what healing compares (`RESOLVES_TO {version}` → Element). Copying would let the two drift.
- 2026-11-03 — Logical name: step schema's `$defs/logicalName` pattern (read from the file), `none.noMatch` refused (galip, #71); malformed/reserved/blank → 400 on `$.name`. Duplicate in the app → 409 whose detail names the existing object's id (FR-07).
- 2026-11-03 — Unknown snapshot (or one of another app) → 400 `$.snapshotId`; unknown element → 400 `$.snapshotElementId`; same as unknown step targets in the tests API. Unknown app → 404.
- 2026-11-03 — No `Location` header: there is no GET for one object yet (#30's repository view).
- 2026-11-03 — The client had no version choice, but the snapshot import needs one: the form lists the app's versions and can add one inline (user approved). The last choice is kept while the Spy is open; otherwise the last listed version.
- 2026-11-03 — Suggestion: primary takes the ADR priority (`automationId` unless generated, `name`, `nearestLabel`, `className`, `parentPath`, then `controlType`) in order, keeping only fields that narrow the matches in this capture, until the element is unique; the rest of the priority is fallback; `windowTitle`, `siblingIndex`, `helpText`, `accessKey` and a generated id start as "Not used". The form shows how many elements of the capture the primary set matches.
- 2026-11-03 — `isGeneratedId` is a TS copy of the agent's `model.is_generated_id` (read only, hasan's code); a test keeps `LOGICAL_NAME` equal to the step schema's pattern, but nothing yet ties the generated-id regexes to the agent's.

## Status
- [x] server endpoint + `RepoObjectIntegrationTest` (6); `./mvnw test` 76/76 on 2026-11-03; `openapi.yaml` regenerated; `docs/graph-model.md` RepoObject row updated
- [x] merged `omer/24-object-spy` (with #17) into this branch, no conflicts
- [x] client: `main/repository.ts` (versions, import + create), IPC + preload, form in the Spy; `npm test` 124/124, lint, typecheck, format, build green on 2026-11-03
- [ ] manual check of the form on macOS (`npm run dev:mock` + real server), see below
- Next step: run the manual check with omer; then ask about push and how to open the PR (branch carries #15, #17, #24).

## Manual checks
- 2026-11-03 · omer · form on macOS: `docker compose up --build` + `npm run dev:mock`, server `http://127.0.0.1:8080` · pending
- Weekly Windows session: the same with a real pilot app window (after #22 for the hotkey pick) · pending

## Open issues
- One Element may back several repository objects (not refused). Decide with #30 whether that is an error.
- Name uniqueness is checked in the transaction, no constraint (same as test names): two concurrent creates of one name can both succeed.
- The "generated id" rule (ADR descriptor v0 §3) lives in the agent (Python); the client needs the same rule to suggest `automationId`, or the agent/snapshot should flag it.

## Handoff
- Response: `{id, appId, name, primary, fallback, resolvesTo: [{appVersionId, elementId, snapshotId, snapshotElementId}], createdBy, createdAt, updatedBy, updatedAt}`.

## Outcome (fill when the issue closes)
