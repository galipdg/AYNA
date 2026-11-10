# Active — Hasan Berk Yanıkkaya (`hasan`)

Only hasan's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-10 (review round of eight PRs, #22 built)
- Current issue: **#22**, on `hasan/22-element-from-point`, three commits, **no PR yet**.
  Criteria 1 and 2 are met and measured; criterion 3 waits on a manual scaling check.
  Everything else is in `memory-bank/tasks/22-element-from-point.md`.
- **No open PRs of mine.** #170, #200, #201, #202 and #210 are all merged, so #161, #26, the
  two coordinate bugs, the #38/#184 notes and #199 are on `main`.
- **Review queue: empty.** Eight approved on 2026-11-10 — omer's #217, #218, #219, #220, #222,
  #223, #224, #225 — including two ADRs: `2026-11-08-run-screenshots-and-retention` and
  `2026-11-08-contracts-v1-freeze`.

## #22, so the next session does not re-derive it

`elementFromPoint(x, y)` answers **out of the snapshot the agent took last**, returning that
snapshot's own element, rather than describing the hit element on its own. Three of the twelve
descriptor properties come from an element's surroundings (`nearestLabel`, `parentPath`,
`siblingIndex`), so describing one element costs a read per sibling *and* would give the same
element two different descriptors — the full reasoning is in `learnings.md` 2026-11-10 and it
applies to anything else that wants a descriptor outside a walk (#23, #54, a recorder).

Reply: `{handle, bounds, snapshotId, elementId, element}`, one shape for every outcome, and a
point is never an error. `snapshotId` null = nothing captured for this window; `snapshotId` set
with `elementId` null = the window changed, capture again; both set = select that node. omer has
this in his inbox, because the Spy's pick hotkey is what consumes it (#184 step 8).

Measured here at 120 DPI: median **3.39 ms**, p95 5.00 ms, worst 7.08 ms over 50 calls, against
#22's 300 ms. 432 agent tests pass, ruff clean.

**Still to do:** the scaling manual check (the task note has the exact steps), the PR with
`Closes #22`, and — once omer's #224 merges — `elementFromPoint` in
`schemas/agent-rpc.schema.json` as a minor bump to 1.1.

## What I promised in the 2026-11-10 reviews

Keep these; they are commitments, not opinions.

- **#54 sends the target *window*, not the desktop** (said on #223). That is what makes omer's
  8 MB screenshot limit safe: I measured a 1920×1080 full-screen PNG at **222 KB** but the
  incompressible ceiling at that resolution at **7.92 MB**, i.e. the limit has no headroom for a
  full screen and none at all above 1080p. A window crop is a fraction of that.
- **#40 does not emit `repairProposed` until #74 is on `main`** (#223's ADR moves the write
  there). The server answers 400 today and under NFR-45 the result would be set aside instead of
  retried, so the healing experiment's own data would end up only in the undelivered file.
- **#61's outbox keeps order per `(runId, stepIndex)`** — the result, then its screenshot — and
  never attempts a screenshot whose result has not been accepted. This is what makes 404
  terminal; "no result yet" and "unknown run" are the same status in omer's contract, and I asked
  him for a 425 but took the ordering obligation either way. A screenshot whose result
  dead-lettered goes straight to `ayna-undelivered.jsonl`.
- **#61's terminal list grew:** 400 (including "not a PNG"), 401, 403, 404, 409, **413**, **415**.
  Retry: connection refused, DNS failure, timeout, 5xx.
- **The whitespace `pattern` on `snapshot.schema.json` and `element.schema.json` is 0.1 → 1.0,
  not 0.2.** Tightening a pattern is breaking under the #52 freeze; I proved it by running omer's
  `schema_compat.py` against my own schema (it rejects the 0.2 bump and allows 1.0). So it needs
  an ADR and all three approvals, after #15 and #24 have landed against 0.1, and the client's
  version-mismatch branch (#186) should expect `1.0`.
- **#221 may need nothing from me.** The column headers are already in every snapshot as
  `Header`/`HeaderItem` elements, so `RepoObject.columns` can be filled from the document the
  server already receives — no snapshot-schema change, no ADR, and it also covers KeePass 2,
  which `GetColumnHeaders` cannot (no TablePattern). Said so on #221; waiting for omer.
- **I will run `server/loadtest/run.sh` on Windows** (#225/#152) and report the `machine` block
  with Docker's NCPU/MemTotal. It cannot run as written: `python3` here is the Microsoft Store
  App Execution Alias stub, so the script dies at `python3 seed.py`. omer has the fix request.
- **#226 is mine to half-build**: the `blocked` flag on `SnapshotTimeout`. Galip owns the
  dispatcher line and the `-32002` doc row.

## Decisions already made — do not re-derive them

**#40 (playback v1):**
- **A primary set that matches more than one element is a failure**, FR-35 *element not found*.
  Playback **never picks the first match**: UIA child order is not stable across runs, so "the
  first" would make RQ2 (#69) measure AYNA's own nondeterminism. An ambiguous target does not
  start healing (FR-29): the remedy is another property, not another element. Fallback properties
  are tried only when the primary set matches **zero**.
- The result field is **`durationMs`**, and the steps to play are `document` from
  `POST /api/runs`, so `stepIndex` is a position in the run's own copy.
- **Rows on KeePass 2** (no Grid/Table pattern): read a row's cells from the `ListItem`'s `Text`
  children in header order; `{value, column}` maps the header text to a child index through the
  `Header`'s `HeaderItem`s. `cell` is grid-only in the schema while `rowExists {value, column}` is
  allowed on a list — the same column mapping, one forbidden and one required. Raised on #220 and
  #221; galip's v0.2 ADR to settle.

**Control types measured** (`eval/spikes/grid-probes.md`): Qt `QTableWidget` → `Table` (Grid +
Table patterns), Qt `QListWidget` → `List`, KeePass 2 `m_lvEntries` → `List` with a `Header` of
five `HeaderItem`s. No pilot app has a WinForms `DataGridView`.

## Windows queue — the next real session

All omer's, all needing this machine:
- **#206** — the step editor's decimal comma and the stale-test-after-rename fix.
- **#204** — the Spy tree's scrolling **smoothness** at ~285 real Chromium-shaped elements, with
  the pane visible, reporting frame times rather than an impression. (The width part is fixed and
  measured; smoothness is the half my #184 note was actually about.)
- **#184** — step 2 (the Turkish fold) and step 6; step 8 is unblocked by #22 now.
- **#38** — the two findings are fixed in #206; re-run its check.
- **#17** — PR #154 is merged, so this is about the edge cases (crash, restart, a stale agent).
- **#225/#152** — the load test, for a second data point. Needs omer's `python3` fix first.
- **#197** — the check popover and the test-list resizer at 100 % **and** 150 %, `npm run demo`,
  and **Ctrl+Z / Ctrl+Y**, which were never pressed (only ⌘Z on macOS).
- New: the **nav at 1280 px** — "Nesne Deposu" is the longest nav label now and it collapses to
  icons below 1180.
- **A second monitor at another scaling is impossible here**: this machine has one 1920×1080
  display. Say that plainly rather than listing it as pending.

## Environment, so it is not re-derived

- `agent/.venv` has pywinauto 0.6.9, ruff 0.17.3 and pytest; the repo-root `.venv` has PySide6 and
  is what the trial app and the Windows playback tests look for. **Python 3.13 only** — a green
  local run is never evidence that the `>=3.11` floor holds (`learnings.md` 2026-11-01). Run ruff
  as `agent/.venv/Scripts/python.exe -m ruff`; the root `.venv` has no ruff.
- **`python3` is a Store stub here**, `python` is the real 3.13.0. Any script that hard-codes
  `python3` fails on this machine.
- Docker **29.6.1** is available. Server address is **`http://[::1]:8080`**, not `localhost`:
  `PEMHTTPD-x64` holds IPv4 8080 and cannot be stopped without elevation. Admin is
  `admin` / `ayna-dev-admin` (the git-ignored `.env`).
- The database is **seeded and stopped, not deleted** (`ayna_neo4j-data` is intact): `AYNA Trial`
  with five repository objects and two tests. `docker compose start` brings it back. The #152 load
  test uses its own project `ayna-loadtest`, so its `down -v` cannot touch this — checked.
- **Rebuild the server when you switch branches** (`docker compose up --build`); nothing ties the
  running image to the checkout. This cost time on #38.
- This display is at **125 % (120 DPI)**, so "100 %" is not the resting state either.
- `client/node_modules` is installed; electron is 45.0.0, well past the Chromium that CSS anchor
  positioning needs. Pilot apps are in `C:\ayna-pilots\` with the demo vault `ayna-demo.kdbx`
  (password `ayna-demo`); `eval/spikes/kp_state.py main` opens KeePass 2's database in ~16 s.
- **Always name the path when running eval tests** (`pytest eval/apps/trial/tests`): #210 fixed
  the module collision, but `eval/spikes/` tests are still in no CI job.

## Open, not mine to close

- Three places answer `rpcVersion` `"0.1"` while #224 freezes the contract at 1.0:
  `agent/ayna_agent/rpc.py:37` (galip's, in his inbox), `client/dev/mock/ayna_agent/rpc.py:77`
  (omer's own, raised on #224) and two lines of `docs/agent-rpc.md`.
- **Nothing enforces the major version on the client ↔ agent link**: the client never reads
  `rpcVersion`, so a 2.0 agent would be used by a 1.x client. Offered to open an issue on #224.
- `DEMO-windows.md` §5.3 step 6 says `user` → 3 matches; the real number is **2** (computed
  against the committed capture). Raised on #218.
- The Spy's `visible` is "Ekranda" while the step editor's `visible` is "Görünür" — the *same*
  UIA property (`not IsOffscreen`, per the step schema's own description). Raised on #218.
- `DEMO.md`'s capture paragraph claims only `snapshotId` and `agentVersion` are test-supplied;
  the whole `capture` block and the `app` block are too. Raised on #217.
- #219's three new Turkish texts say "ajan", which #218's new test rejects — whichever merges
  second breaks `main` unless they are changed. Raised on both.
- Galip still owes, from earlier reviews: the model-server-not-running 504 `timeout` decision on
  Windows (#173), #173's IPv6 listen address, #176's explicit LF newline, and the one-sided `dpi`
  fallback in the healing scorer (#166). Plus #150's ADR sentence about KeePass 2 ListItems.
- **PR #138** is empty and should be **closed, not merged**.
- **Branch `hasan/2209a-application`**: created from `main`, no commits, not mine. Find out whose.
- **`copilot-swe-agent[bot]`** has pushed to branches of mine and once left a `<<<<<<< HEAD`
  marker in `memory-bank/decisions/README.md` on `main`. Its `COMMENTED` review is not an
  approval.
- Inbox: handled through 2026-11-05. Do not delete the handled lines yet — open PRs still append
  to that file and `merge=union` would bring deletions back.
