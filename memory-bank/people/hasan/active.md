# Active — Hasan Berk Yanıkkaya (`hasan`)

Only hasan's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-07 (review round: twelve PRs)
- Current issue: **none in progress.** The session was a review round, not a build.
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
4. **TODO — `docs/AGENTS.md`**: give `ui/` to omer, refresh the stale Layout list (`ui/`,
   `graph-model.md`, `tool-matrix.md`, `agent-rpc.md`, and `manual-checks/` from root §10), and fix
   the pre-ADR ownership tables in `docs/working-agreement.md` §1 and `docs/README.md` (galip's #19
   note). **Needs the user's OK** (root §7: changing an `AGENTS.md` requires asking).

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

## Windows queue — the next real session

`gh issue list --label needs-windows-test` → **#184, #38, #17** (all omer's). Run **#184 first**: it
saves the elements #38's check uses. Beyond the steps on the issues, I said I would also take:

- #184 step 7 **on a second monitor at a different scaling**, not only at 150 % on one. The overlay
  uses `screen.screenToDipRect`, which picks the scale of the display the rectangle is on — correct,
  and the straddling case is the untested one. **Every snapshot number we have is from one 120-DPI
  display**, so this is unmeasured territory generally.
- #184 step 6 **on a real pilot window**, not only omer's synthetic 3031-element tree. The capture
  may not finish: the agent's default budget is 5 000 ms and the client sends no `timeoutMs`, so a
  window like KeePass 2's (278.5 s in #161) times out with `-32002` and "Capture again" retries the
  same budget. I asked omer for a bigger budget on retry (#186). Report the budget separately.
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

## Found while running the follow-ups — worth its own issue, not mine to sneak in

`eval/` has **two different modules named `uia_dump.py`** (`apps/trial/` and `spikes/`). Each tree
is green alone but `pytest eval/` from the repo root fails 26 of 38, because one shadows the other.
Hidden today by `testpaths = ["apps/trial/tests"]` and by CI running only the trial tests. Details
and the three fix options in `learnings.md` 2026-11-07; the fix touches omer's CI job, so propose an
issue rather than changing it. **Always name the path when running eval tests.**
