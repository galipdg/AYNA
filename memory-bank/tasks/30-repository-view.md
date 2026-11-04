# #30 Repository view

- Issue: https://github.com/galipdg/AYNA/issues/30
- Owner: omer · Branch: `omer/30-repo-view` (stacked on `omer/185-ui-language`, which carries #25's repository API and the i18n rule)
- Started: 2026-11-03 · Last update: 2026-11-04

## Approach
Screen from `docs/ui/wireframes.md` §5: objects grouped by screen (the part before the dot) with a test count, search by name/label/type; details on the right with Rename, Edit (same Find by / Backup editor as Add to repository), Used by, Seen in versions, Remove.
Server (`server/.../repository/`), next to #25's `POST /api/apps/{appId}/repo-objects`:
- `GET /api/apps/{appId}/repo-objects` — every object with `testCount` and a short element summary (controlType, nearestLabel).
- `GET /api/repo-objects/{id}` — the object with `usedBy` (tests) and the resolved Element's descriptor of the latest version (for the editor).
- `PATCH /api/repo-objects/{id}` `{name?, primary?, fallback?}` — same checks as create; 409 when the name is taken. Steps keep working: `TARGETS` points at the object id, not its name (FR-08).
- `DELETE /api/repo-objects/{id}` — 204; 409 when a step targets it, the message names the tests (FR-09).

## Decisions (small, local to this task)
- 2026-11-03 — API shape above, single object under `/api/repo-objects/{id}` like `/api/tests/{id}` (user approved).
- 2026-11-03 — "Create" in the acceptance criteria = the Spy's Add to repository (#25), reached by the screen's "Open Object Spy" button; no element-less objects (user's choice, matches the wireframe).
- 2026-11-03 — One Element may back several objects: allowed; the Spy's add form warns that the element is already saved as X (user's choice). Every capture makes new Element nodes, so "the same element" in the warning means: an existing object's primary set matches the picked element, not the same node.
- 2026-11-03 — PATCH replaces `primary` and `fallback` together (one without the other → 400): checking a new primary against an old fallback would let the two sets overlap. A PATCH that changes nothing writes nothing (`updatedAt` stays).
- 2026-11-03 — "Latest" element = the RESOLVES_TO Element whose Window has the newest `capturedAt` (AppVersion has no order besides its version string).
- 2026-11-03 — Delete removes only the RepoObject and its links; the Elements stay with their snapshot.
- 2026-11-03 — Edit in the repository has no capture, so it shows no "N elements match" count (the Spy's form has one); the rows start from the object's own values, then the last captured element's.
- 2026-11-03 — "Used by" lists test names as plain text: the Tests screen (#38) is not built, so there is nothing to open yet.
- 2026-11-03 — The client tells a DELETE 409 (in use) from a PATCH 409 (name taken) by the server message; known server texts (`objectInUse`, `objectGone`) are mapped in both languages.

## Status
- [x] server: list, get, patch, delete + 7 integration tests; `./mvnw test` 83/83 on 2026-11-03; `openapi.yaml` regenerated
- [x] client: main/IPC/preload, `Repository.tsx`, Shell place enabled, tr/en texts; the Find by / Backup editor moved to `PropertySetEditor.tsx` (shared with Add to repository); lint, typecheck, format, `npm test` 156/156, build green on 2026-11-03
- [x] Spy add form: "already saved as" warning (`objectsMatching` in `shared/repository.ts`)
- [x] agent smoke run on macOS against the real server (below)
- [x] omer's manual check on macOS (2026-11-04, pass); Windows look at the weekly session
- [x] Pushed, PR #191 opened 2026-11-04 (base main, stacked on #190); reviewers galip, hasan
- Next step: answer the PR #191 reviews; Windows look at the weekly session.

## Manual checks
- 2026-11-03 · agent · macOS, `docker compose up --build` + `electron-vite dev` with the fake agent, driven over CDP; seeded app "Repo View Check" (versions 1.0, 1.1; trial-login capture under 1.1; 3 objects; 2 tests on login.userNameInput) · list grouped by screen with test counts; details (used by, find by, seen in 1.0 – / 1.1 ✓); remove of a used object refused naming both tests; rename to a taken name refused, to a free one kept the steps (GET test shows the new target); edit moved nearestLabel to Find by; remove of an unused object; search by plain type, by label, no match; English texts; Spy add form warns "looks saved already as login.kullaniciAdiInput" · pass · evidence: screenshots in the session only
- 2026-11-04 · omer · same setup, app "Repo View Check": list and test counts, remove of a used object refused naming the tests, rename, edit, English · pass · the agent did not start because the dev command was split over two lines (env vars not passed); the Repository screen does not need the agent

## Open issues
- Delete uses `DETACH DELETE`: a HealingProposal `FOR` the object (#74) would lose its link. None exist yet; #74 should decide (refuse, or delete the proposals too).

## Handoff

## Outcome (fill when the issue closes)
