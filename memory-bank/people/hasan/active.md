# Active — Hasan Berk Yanıkkaya (`hasan`)

Only hasan's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-07 (review round, #26 built, Windows session, two coordinate bugs)
- Current issue: **#26 is done** (PR #200, `Closes #26`, both criteria measured). Nothing else in
  progress.
- **My open PRs, in merge order:**
  1. **#170** (`hasan/161-winforms-walk`, `Closes #161`) — 5/5 CI green, both approvals,
     `MERGEABLE`. **Waiting only on the merge click.** The `ai` job that blocked it for days was
     galip's flaky request-log race; re-running the job made it green.
  2. **#200** (`hasan/26-minimal-playback`, `Closes #26`) — CI 5/5 green. Two of its commits are
     in galip's `rpc.py` and `docs/agent-rpc.md` on purpose, each on its own, so he can take,
     move or redirect them.
  3. **#201** (`hasan/dpi-awareness-v2`) — the two coordinate bugs below. Small, two commits.
- **#198 is merged** (`9a95381`), so the four review follow-ups are on `main`.
- **The G0 chain (#28) ran end to end on Windows today and works.** Spy → Neo4j → playback by
  logical name, with the application confirming "Welcome, admin!". I ticked three of #28's four
  criteria; **the remaining one is galip's #7** (a 7–8B model returning valid JSON for a Turkish
  prompt). Evidence is a comment on #28.
- **Review queue: empty.** All twelve PRs that were waiting on me are approved (2026-11-07):
  galip's **#150**, and omer's **#182, #186, #187, #188, #189, #190, #191, #192, #193, #194,
  #197**. Two ADRs approved with them: `2026-11-03-client-ui-language` and
  `2026-11-05-runs-api-and-live-updates`.
- My open PRs: **#170** (`hasan/161-winforms-walk`, `Closes #161`) only. Both approvals are in,
  `MERGEABLE`, and the four module jobs pass; the **`ai` job fails on galip's request-log race in
  `_send`**, which has nothing to do with this PR. It merges when galip fixes that. **#169 and
  #180 are merged** (D1 ADR and #12).
- Still to tick by hand: **#161's five acceptance boxes on the issue** — PR #170 ticks them, the
  issue does not.

## What the review round committed me to

All on branch `hasan/review-round-1107` / **PR #198**. Three of the four are **done** (`d00c491`):

1. **DONE — `recognition/snapshot.py`: `loads` now refuses a level-order document.** It checked
   only that a parent appeared earlier; omer's Java `SnapshotSchema.treeError` enforces
   **contiguous subtrees**, which is what the schema's text ("in pre-order") means, so the agent
   could hand the server a document it answers with a 400. `loads` now tracks the current path the
   way the server does, and the module docstring no longer states the weaker rule. New test
   `test_loads_refuses_an_element_outside_its_parents_subtree`; `test_loads_refuses_a_second_root`
   now matches the clearer message. 281 agent tests pass.
   - **The cases.json half of that promise was wrong and is withdrawn.** Every `invalid` case in
     `schemas/examples/snapshot/cases.json` must name the **JSON Schema keyword** that rejects it
     (`"rule"`), and a level-order document is schema-*valid* — no keyword rejects it. Adding it
     would have broken both my `test_a_named_invalid_case_is_refused_by_the_rule_it_names` and
     omer's `everyInvalidCaseIsRejected`. Structural rules are correctly tested on each side
     separately; no `schemas/` change was needed, so no ADR and no team approval either. Said so on
     #182.
   - The client's `buildTree` is equally permissive, which is fine — being liberal in what you
     display is right for a Spy — but its comment claims pre-order; omer has that note on #186.
2. **DONE — `model.py`: `nearest_label_source` is in `NEVER_MATCH`**, with omer's reason.
   **The ADR was deliberately not touched:** `2026-10-31-element-descriptor-v0` is Accepted, the
   root rules say never edit an accepted ADR, and that ADR already names `model.NEVER_MATCH` as the
   list ("with the reason in the code"). So the code is the only place this belongs. If the team
   wants the ADR's enumeration to be authoritative, that needs a superseding ADR — not worth one
   for a property nobody matches on, but it is the team's call, not mine.
3. **DONE — `eval/spikes/grid_probe.py`**, `grid_probe_app.py` and `grid-probes.md`. Both runs are
   reproduced through the committed script: the Qt table and list (galip asked for this one on
   #150) and KeePass 2's `m_lvEntries`. Deliberately **does not import `kp_state.py`**, which lives
   on `hasan/161-winforms-walk` and is not on `main` yet — it takes a window handle instead, so
   #198 does not depend on #170's merge order.
4. **DONE — the `docs/` ownership cleanup**, with the user's OK (asked, per root §7).
   `docs/AGENTS.md` gives `ui/` to omer and its Layout list now names every folder and document
   that exists plus the four that do not yet (`ui/`, `report/`, `manual-checks/`, `literature/`),
   so the next person puts a new file in the right place. `docs/README.md` names the carve-outs
   instead of implying all of `docs/` is mine. `docs/working-agreement.md` §1 is the post-ADR
   split, with a paragraph saying why `recognition/` moved and that the root `AGENTS.md` §2 table
   must change with it (galip's #19 note, closed).

## Decisions I made in the reviews — do not re-derive them

**#40 (playback v1):**

- **A primary property set that matches more than one element is a failure**, categorised as
  FR-35 *element not found*: no unique element matched. Playback **never picks the first match** —
  UIA child order is not stable across runs, so "the first" would make RQ2 (#69) measure AYNA's own
  nondeterminism instead of the application's. An ambiguous target does **not** start healing even
  though the search was complete (FR-29): the remedy is another property, not a different element.
  The failure message says how many matched. #63's decision log carries the count.
  Fallback properties are tried only when primary matches **zero**, never when it matches several.
- **The result field is `durationMs`, not `duration`** (#193's ADR handed me the name). Unit-carrying
  names everywhere else, and the step-schema v0 ADR explicitly rejected `timeout_ms`. omer and galip
  both have the request; `docs/agent-rpc.md`'s "#40 (duration, message)" line is galip's to change.
- The steps to play are `document` from `POST /api/runs` — the run keeps a **copy** of the steps, so
  `stepIndex` is a position in that copy and editing the test mid-run cannot shift a sent result.
- Rows on KeePass 2 (no Grid/Table pattern): read a row's cells from the `ListItem`'s `Text`
  children in header order, so `rowExists {value}` matches **any** column and `{value, column}` maps
  the header text to a child index through the `Header`'s `HeaderItem`s. See `learnings.md`.

**#61 (CLI runner outbox), now that #193's status codes exist:**

- **Retry:** connection refused, DNS failure, timeout, 5xx.
- **Terminal → `ayna-undelivered.jsonl`, exit 2:** 400 (NFR-45), 401, 403, **404** (a deleted test
  takes its runs, so an unknown run is permanent) and **409** (another body for the same key is a
  client bug; the stored body is the one that counts).
- Keep each outbox entry as **the exact bytes that were sent**, not a rebuilt object, so a retry is
  byte-identical. omer's server canonicalises recursively (`sorted()` + SHA-256, arrays keep order),
  so a re-serialising client is safe too — but byte-identical needs no such guarantee.
- **#40 must not emit `repairProposed` until #51 and #74 are on `main`**: the server answers 400
  today, and under NFR-45 the result would be set aside instead of retried — the healing
  experiment's own data would end up only in the undelivered file.

**#22 (element under cursor), the shape omer can build against:** a method taking a physical-pixel
point and returning the deepest element at it as a descriptor **plus**, when a snapshot of that
window is open, the matching snapshot element `id`, so the Spy selects the tree node it already has
instead of re-deriving it from `bounds`. The client already converts the cursor correctly
(`screen.dipToScreenPoint`), so the point arrives in physical pixels.

## Two coordinate bugs of mine, found at a real scaling (PR #201)

Both were invisible on one 120-DPI display and in every unit test, and both are written up in
`learnings.md` 2026-11-07:

1. **The agent had never been per-monitor-v2 DPI aware**, although `docs/agent-rpc.md` and
   `snapshot.schema.json` both promise it. `DPI_AWARENESS_CONTEXT` is pointer-sized; my ctypes
   call truncated it, failed with `ERROR_INVALID_PARAMETER` (87), my code treated 87 like 5
   ("already set") and logged success, and pywinauto's import then set per-monitor-**v1**.
   `GetAwarenessFromDpiAwarenessContext` cannot tell v1 from v2 — only
   `AreDpiAwarenessContextsEqual` can, which is what `dpi_awareness()` now uses.
   **No measurement is invalidated:** v1 and v2 are both unscaled.
2. **`listWindows` reported `GetWindowRect`**, which includes Windows 10's *invisible* resize
   border (8 px at 150 %), so the Spy framed a window 8 px too wide. One window has three
   rectangles — `GetWindowRect` 472×261, DWM extended frame bounds 456×253, UIA 450×213 (no title
   bar). It now reports DWM's. **"bounds" is not one concept on Windows**; any new consumer (#54's
   crop, #23's fallback) has to say which it means.

**The lesson worth keeping: a success log is not evidence.** The first bug said "already set" for
weeks on a call that had never worked. When an API's outcome is load-bearing for a contract, read
the state back.

## Windows queue — the next real session

**#184 is done: six of eight steps pass**, result posted as a comment. The label stays for step 2
(the Turkish fold, and the trial app having no Turkish text at all) and step 6's smoothness (not
smooth at 285 *real* elements, while omer's synthetic 3031 were). Step 8 needs #22.

**Still queued: #38 and #17.** The environment is proven now, so they are cheaper than #184 was:

- Server address is **`http://[::1]:8080`**, not `localhost` — `PEMHTTPD-x64` (EnterpriseDB's
  Apache, auto-start service) holds IPv4 8080 on this machine and cannot be stopped without
  elevation. Compose binds `[::]` too, which is the way in.
- Admin is `admin` / `ayna-dev-admin` (the `.env` I wrote today; it is git-ignored).
- `AYNA Trial` application with version `0.1-dev` and three repository objects
  (`login.userNameInput`, `login.passwordInput`, `login.loginButton`) are already in the database.

What I would still take beyond the steps on those issues:

- **A second monitor at another scaling is not "pending" — it is impossible here.** This machine
  has one 1920×1080 display. Stop listing it as a weekly-session item until there is a second
  monitor; say so plainly instead.
- The 5 s capture budget is **comfortable for Chromium-class windows** (VS Code 285 elements in
  723 ms, Opera 456 in 1321 ms, no timeout), so my #186 worry about not being able to raise it
  stands for WinForms (#161's 278.5 s), not for these. Try it on KeePass 2 when #38's check runs.
- #197: the check popover (anchored, survives scrolling, Esc, not clipped) and the test-list resizer
  at both ends of 150–420 px, at 100 % **and** 150 %; `npm run demo` including its Docker and
  wrong-password messages; **Ctrl+Z / Ctrl+Y**, which were never pressed (only ⌘Z on macOS).
- **#184's step 2 fails as written** until omer fixes the Turkish fold ("giris" does not find
  "Giriş"). Do not report that as a code failure before he has decided.

## Open, not mine to close

- **#150's ADR has one wrong sentence** (KeePass 2 ListItems "have no cell children" — they have
  five `Text` children each) and one wrong reason ("a list has no columns" — that list has a Header
  with 5 HeaderItems). Galip has it in his inbox and on the PR; he flips the ADR to Accepted in
  that PR anyway.
- **`2026-10-27-step-schema-v0` is flipped to Accepted by #150's own commit `a759985`.** So
  `docs/sdd/SDD.md`'s "Three ADRs are still Proposed" goes stale the moment #150 merges — omer has
  that on #194. `2026-10-31-accounts-and-tokens` is in the same position (condition met 2026-11-01,
  status not flipped). **`2026-10-31-element-descriptor-v0` is Accepted** — my earlier note that it
  was still Proposed was wrong.
- Galip still owes, from my earlier reviews: the model-server-not-running 504 `timeout` decision on
  Windows (#173), #173's IPv6 listen address, #176's explicit LF newline, and the one-sided `dpi`
  fallback in the healing scorer (#166).
- **`minLength: 1` cannot say "not only spaces"** in `snapshot.schema.json` and
  `element.schema.json`. Recommendation unchanged: a non-whitespace `pattern` on every string
  property in both, one PR bumping both to 0.2, after #15 and #24 land against 0.1. Note that
  bumping the snapshot schema will make the client's `parseSnapshot` call a 0.2 document
  `bad-response` until omer adds a version-mismatch branch (#186).
- **PR #138** is empty and should be **closed, not merged**; `docs/requirements-workshop.md` §7 is
  on `main` as the empty template (#19, galip's).
- **Branch `hasan/2209a-application`**: created from `main`, no commits, not mine. Find out whose.
- **`copilot-swe-agent[bot]`** has pushed to branches of mine and once left a `<<<<<<< HEAD` marker
  in `memory-bank/decisions/README.md` on `main`. Check that file whenever it touches my branches;
  its `copilot-pull-request-reviewer` COMMENTED review is not an approval.
- Inbox: handled through 2026-11-05, **including omer's #21/#161 note** (both branches pulled; #169
  merged). Do not delete the handled lines yet — open PRs still append to that file and
  `merge=union` would bring deletions back.

## Environment, so it is not re-derived

`agent/.venv` and a repo-root `.venv` both exist with pywinauto 0.6.9 on **Python 3.13 only** — a
green local run is never evidence that the `>=3.11` floor holds (`learnings.md` 2026-11-01).
`client/node_modules` is installed; `electron` is **45.0.0**, well past the Chromium that shipped CSS
anchor positioning, which #197's check popover needs. Pilot apps are in `C:\ayna-pilots\`
(`keepass2`, `keepassxc`, `handbrake`, `notepadpp`) with the demo vault `ayna-demo.kdbx`
(password `ayna-demo`). `eval/spikes/kp_state.py main` brings KeePass 2 to a database-open state in
about 16 s and prints the window handle. Docker and Java 21 were **not** available in the
2026-11-01 session and were not needed in this one.

## Found while running the follow-ups — now issue #199

`eval/` has **two different modules named `uia_dump.py`** (`apps/trial/` and `spikes/`). Each tree
is green alone but `pytest eval/` from the repo root fails 26 of 38, because one shadows the other.
Hidden today by `testpaths = ["apps/trial/tests"]` and by CI running only the trial tests. Opened as
**#199** (assigned to me) with three options; my preference is `--import-mode=importlib`. The fix
touches `eval/pyproject.toml` and possibly omer's CI job, so it needs his agreement.
**Always name the path when running eval tests**, and treat a batch failure there as this collision
until proved otherwise. Also note `eval/spikes/` tests are in no CI job at all.
