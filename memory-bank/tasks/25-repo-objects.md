# #25 Add element to the object repository

- Issue: https://github.com/galipdg/AYNA/issues/25
- Owner: omer · Branch: `omer/25-repo-objects` (stacked on `omer/15-snapshot-import` until PR #182 merges; the client part also needs `omer/24-object-spy`)
- Started: 2026-11-03 · Last update: 2026-11-03

## Approach
Server: `POST /api/apps/{appId}/repo-objects`, body `{name, snapshotId, snapshotElementId, primary, fallback}` (`server/.../repository/`). The client first imports the picked element's snapshot (#15, idempotent), then posts the object; the server finds the Element by `(snapshotId, snapshotElementId)`, checks the snapshot is in this application, and writes `(Application)-[:HAS_OBJECT]->(RepoObject)-[:RESOLVES_TO {version}]->(Element)` in one transaction.
Client: the Spy's `VersionBar.tsx` chooses (or adds) the application version once. "Add to repository" under the property panel (#24) opens `renderer/src/AddToRepository.tsx`: a name, a summary of how AYNA finds the element (the "Find by" properties, whether only this element matches, the backups), and "Advanced settings" with one row per identifying property (editable value; Find by / Backup / Don't use). Suggestions come from `shared/repository.ts` `suggestUses`. Main process `main/repository.ts` imports the snapshot under the version, then creates the object.

## Decisions (small, local to this task)
- 2026-11-03 — App-scoped path `/api/apps/{appId}/repo-objects` instead of the issue's `/api/repo-objects`: matches the tests API (user approved).
- 2026-11-03 — `primary` / `fallback` stored as JSON strings (property → value, insertion order = best first), as `Step.checkpoint`; they are always read and written whole (user approved).
- 2026-11-03 — Allowed keys = the element descriptor's properties (`snapshot.schema.json#/$defs/element`) minus `NEVER_MATCH` (`bounds`, `dpi`, `nativeWindowHandle`, `frameworkId`, `enabled`, `offscreen`) and `nearestLabelSource`. Read from the schema, so win32 properties (#23) become allowed when the schema gets them. Values are type-checked against the schema only; they may differ from the Element's values, since the user may edit them.
- 2026-11-03 — `bounds` and `dpi` are **not** copied onto RepoObject (the design preview had them): they stay on the resolved Element (#15 stores them), which is what healing compares (`RESOLVES_TO {version}` → Element). Copying would let the two drift.
- 2026-11-03 — Logical name: step schema's `$defs/logicalName` pattern (read from the file), `none.noMatch` refused (galip, #71); malformed/reserved/blank → 400 on `$.name`. Duplicate in the app → 409 whose detail names the existing object's id (FR-07).
- 2026-11-03 — Unknown snapshot (or one of another app) → 400 `$.snapshotId`; unknown element → 400 `$.snapshotElementId`; same as unknown step targets in the tests API. Unknown app → 404.
- 2026-11-03 — No `Location` header: there is no GET for one object yet (#30's repository view).
- 2026-11-03 — The client had no version choice, but the snapshot import needs one: first in the form (list + inline add); after the manual check moved to a bar at the top of the Spy, chosen once (user's choice). The choice is kept while the Spy is open; otherwise the last listed version. #183 moves it into the app shell's top bar.
- 2026-11-03 — Form redesign after the manual check (omer found the first form hard to use and to present): only the name is needed in the common case; the properties are a short summary ("How AYNA finds it"), the table sits under "Advanced settings" and opens itself when a property problem blocks saving. Plain words in the UI: Name, Find by / Backup / Don't use; API and graph keep primary/fallback.
- 2026-11-03 — Suggestion: primary takes the ADR priority (`automationId` unless generated, `name`, `nearestLabel`, `className`, `parentPath`, then `controlType`) in order, keeping only fields that narrow the matches in this capture, until the element is unique; the rest of the priority is fallback; `windowTitle`, `siblingIndex`, `helpText`, `accessKey` and a generated id start as "Not used". The form shows how many elements of the capture the primary set matches.
- 2026-11-03 — `isGeneratedId` is a TS copy of the agent's `model.is_generated_id` (read only, hasan's code); a test keeps `LOGICAL_NAME` equal to the step schema's pattern, but nothing yet ties the generated-id regexes to the agent's.

## Status
- [x] server endpoint + `RepoObjectIntegrationTest` (6); `./mvnw test` 76/76 on 2026-11-03; `openapi.yaml` regenerated; `docs/graph-model.md` RepoObject row updated
- [x] merged `omer/24-object-spy` (with #17) into this branch, no conflicts
- [x] client: `main/repository.ts` (versions, import + create), IPC + preload, form in the Spy; `npm test` 124/124, lint, typecheck, format, build green on 2026-11-03
- [x] manual check 1 of the form: works, but hard to use → redesigned (version bar, summary + Advanced settings, plain labels); lint, typecheck, `npm test` 124/124, format, build green on 2026-11-03
- [x] manual check 2 of the redesigned form on macOS: functions pass; layout and wording move to #183/#184/#185
- Next step: ask about push and how to open the PR (branch carries #15, #17, #24). Then #183 (UI design first), #184, #185.

## Manual checks
- 2026-11-03 · omer · form on macOS: `docker compose up --build` + `npm run dev:mock`, server `http://127.0.0.1:8080` · steps 1–7 and 9 pass (save, 409 naming the object, name hint, no-primary message); step 8 unclear (the red frame seen was the Spy highlight from #24, not the form). Verdict: the form works but is hard to use and understand; omer wants the UI redesigned before the PR. Evidence: fake-agent and server logs in the session, no errors.
- 2026-11-03 · omer · redesigned form on macOS, same setup · all 7 steps pass; still not clear enough for users → the whole client UI is redesigned in #183 (design + shell), #184 (three-panel Spy, takes over this form) and #185 (Turkish/English)
- Weekly Windows session: the same with a real pilot app window (after #22 for the hotkey pick) · pending

## Open issues
- The whole client is plain and has no navigation; the team finds it hard to use and explain → #183 (design + shell, Week 3), #184 (Spy in three panels, Week 3), #185 (Turkish/English, Week 4).
- One Element may back several repository objects (not refused). Decide with #30 whether that is an error.
- Name uniqueness is checked in the transaction, no constraint (same as test names): two concurrent creates of one name can both succeed.
- The "generated id" rule (ADR descriptor v0 §3) lives in the agent (Python); the client needs the same rule to suggest `automationId`, or the agent/snapshot should flag it.

## Handoff
- Response: `{id, appId, name, primary, fallback, resolvesTo: [{appVersionId, elementId, snapshotId, snapshotElementId}], createdBy, createdAt, updatedBy, updatedAt}`.

## Outcome (fill when the issue closes)
