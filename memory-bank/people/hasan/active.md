# Active — Hasan Berk Yanıkkaya (`hasan`)

Only hasan's agent edits this file. Overwrite it at every session end.

- Last update: 2026-10-29
- Current issue: none in progress. #6 is done, waiting for galip's review as PR #159.
- Branch: `hasan/6-uia-dumps` (PR #159 open, `Closes #6`, CLEAN)
- Next step: **#161** — reproduce the KeePass 2 window state from #6 (database open, Add Entry
  dialog) and bisect the 278.5 s walk. It is Week 2 and #12 cannot size a snapshot budget without
  it. Then **#122** (`eval/` pyproject + ruff), which omer's CI job waits on and which also
  carries the `docs/working-agreement.md` §1 / `docs/README.md` ownership fix.

## This session: the review queue, cleared and merged

**Reviewed 12 PRs.** The 11 in my queue (#135, #138, #141–#146, #150, #151, #157) plus #163
(omer's problem-details ADR, which arrived mid-session). Also gave two **late** reviews on
already-merged PRs whose ADRs were stuck: **#134** (step schema v0 — my review was never requested
and it merged the same day) and **#156** (graph schema v0.1 — merged with *zero* reviews).

Approved: #141, #142, #144, #145, #146, #151, #163, and #135/#143/#157/#138 after converting my
comment reviews once I had judged the asks post-merge. **Only #150 is still held**, on content.

**Eight PRs merged** (#141, #142, #143, #144, #145, #146, #135, #151). I did the mechanical side
with the user's approval: `git merge origin/main` + push on nine of galip's branches to clear
GitHub's union-driver conflict flag, re-synced after every single merge (nine rounds — see
`learnings.md`), and resolved three real conflicts: the ADR index twice and `docs/agent-rpc.md`
once. Every push was a fast-forward; no content of galip's changed except the two ADR status
lines below.

### Reviews worth remembering, because they were measured rather than argued

- **Qt grid probe (#150):** answered all four of galip's UIA questions on a real `QTableWidget`
  and found **two defects in step schema v0.2** — the "ValuePattern first" rule reads `''` for
  every Qt cell (text is in `Name`), and a `cell` check can never be valid against a list
  (`column` required, lists have no headers). Also: every descendant of a Qt table carries the
  table's own AutomationId.
- **Scorer run (#141):** a *wrong* Win32 toolbar button scores **0.800** against a target with no
  id and no Name, and the score is not comparable across targets (1.000 / 0.333 / 0.158 for a
  1 / 3 / 11-property target), so **#73's minimum score must be derived per target, not a
  constant**. The location cut-off is in physical pixels: the same move scores 0.36 at 100% and
  0.20 at 125%.
- **#145:** verified all six objects in `eval/nl/objects/trial.json` live against the running
  trial app — galip had marked that unverified.
- **#142:** found the *cause* of the grid behaviour galip flagged to me: the prompt itself says
  `name` is "the text shown by a label, message, button or **table**".
- **WinForms cost:** plain property reads 2.79 ms/element, the ten pattern probes 1.56 ms, so
  finding 7's pattern-probe hypothesis does **not** hold. Corrected it in
  `eval/spikes/uia-dump.md` and on #143/#138, since I had overstated it in both reviews.
- **No Ollama on this machine**, so every LLM latency we have is from galip's M2 — where the
  service's p95 is 25.3 s and its 30 s deadline already fires. Hence #162.

### Sign-offs I gave (binding; others build on them)

- **NFR-02** (2 s snapshot): confirmed **only** scoped to the sample app.
- **NFR-04** (500 ms/step): confirmed if it says what it measures and exempts #150's polling
  checkpoints. **NFR-05** (10 000 ms): confirmed, with `timeoutMs: 0` documented as legal.
- **TBD-5:** confirmed **plus a third failure state** — "the search ran out of budget" must not be
  "element not found", or healing ranks candidates from an incomplete tree. Raised on #143, #138,
  #144 and #157.
- **TBD-6:** confirmed. **RQ2** (#69): confirmed with an app reset between runs, per-step
  comparison, and the 10-run detection limit stated.
- **RQ1** (#64): **refused as defined** — `parentPath` + `siblingIndex` identify everything, so
  the metric is vacuous. Gave omer exact replacement wording on #157.
- **CLI runner exit codes** (#61): 0 all passed and delivered · 1 a test failed or proposed a
  repair · 2 operational failure even if every test passed.
- **camelCase at every contract boundary**, snake_case only inside Python modules (#11 is mine to
  align). **`parentPath`** = programmatic ControlType names joined by `/`, never localised.

## Open, not mine

- **#150** — held by me. Galip needs to fix two sentences; I posted the exact replacement text and
  will approve the moment it is pushed. It is a `schemas/` freeze document (#52).
- **#138** — now **empty** (0 files): #143 was stacked on it and carried its content to `main`.
  It should be **closed, not merged**. Side effect: its own "do not merge until §7 is filled" gate
  was bypassed, so `docs/requirements-workshop.md` is on `main` with §7 still the empty template
  saying nothing in §2–§5 is agreed. #19 is open, so it is tracked; galip must fill §7.
- **Two ADRs still say Proposed although their condition is met:** `2026-10-27-step-schema-v0`
  (I gave the third approval on #134; galip to flip, and #150 touches the file) and
  `2026-10-29-graph-schema-application-links` (I approved on #156; needs galip's, then omer
  flips it). I flipped `agent-rpc-v0` and `healing-proposal-transport` myself, with the user's OK.
- **Checklist nit:** #141, #142, #145, #146 left the conditional "ADR added" DoD line unticked
  although every merged PR in the repo ticks it with the reason inline. Told galip on #141.
- **#159** (mine) waits on galip's review; #6 cannot close without it.

## Open questions

- A branch `hasan/2209a-application` appeared mid-session and the main checkout was switched to
  it. It was created from `main`, has **no commits**, and I did not create it — possibly another
  session. I left it alone and worked from a worktree. Worth finding out whose it is.
- #9 / PR #116 merged, so ask omer whether it satisfies #2's last criterion ("all three members
  merged one test PR").
- Inbox: omer's #3 CI-skeleton review; omer's two #8 criteria that disagree between the issue and
  PR #121 — I asked galip on #138 to settle it in §7, since the 27 Oct meeting is the likely
  answer.
- Proposed, needs an ADR: replace the single `learnings.md` with a directory of dated one-fact
  files, so append-only memory stops causing the merge cascade (`learnings.md`, 2026-10-29).
