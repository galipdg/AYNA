# Active — Hasan Berk Yanıkkaya (`hasan`)

Only hasan's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-01 (third session of the day: the #169 review answers)
- Current issue: **#21 / PR #169** (D1 pilot-apps ADR). All six review points are pushed,
  `origin/main` merged twice, **no conflict**, CI green on the four jobs that had reported.
  Waiting only on galip's and omer's **approval**; the ADR is still `Proposed` and the single
  remaining change in that PR is flipping it to `Accepted`.
- My open PRs, in merge order:
  1. **#169** `hasan/21-pilot-apps-adr` — `Closes #21`. Merges **first**: #170 is stacked on
     it, and the ADR cites `eval/spikes/uia-walk-cost.md`, which only reaches `main` with #170.
  2. **#170** `hasan/161-winforms-walk` — `Closes #161`. Galip's review is answered; waiting
     on his re-review.
  3. **#180** `hasan/12-snapshot-export` — `Closes #12`, CI 5/5 green, waiting on both reviews.
     Its ADR `2026-11-01-snapshot-schema-v0` is `Proposed` and needs all three of us.
- Review queue: **omer's #179** (local accounts, roles, user management, #60) is waiting for me
  and I have not looked at it yet. That is the first thing to do next session.

## What the #169 session settled (2026-11-01)

Both reviewers **agree with the decision** (PySide6 for #33; KeePass 2 and HandBrake as pilots;
KeePassXC conditional; Notepad++ the #23 fixture) and both deliberately commented rather than
approved, because approval freezes the ADR. The six changes they asked for are in:

- **#161 does not reopen the ADR.** The reopening condition was "WinForms is inherently
  unreadable"; #161 refuted it. Galip's quoted figure (154 elements in 1.79 s) was the
  pre-deduplication run, so I corrected it in the PR comment: **114 elements in 1.86–2.26 s over
  six runs**, and the modal-box reproduction (single root, so unaffected by the dedup fix) at
  **230.05 s for 85 elements**, 2.71 s per element against the dump's 2.63 s.
- **`#22` is gone from the ADR.** Galip was right that it is "element under cursor". I checked
  every open issue: **no semester-1 issue upgrades a pilot app**, so the version-drift role had
  nowhere real to point. #46/#47 are versions of *our* sample app and #42 and RQ4 (#76) run on
  those. Worth not re-deriving — the question will come back at #64 and #46.
- **P1 = HandBrake, P2 = KeePass 2.** I verified galip's SC-07 reasoning against the dumps
  myself: KeePass 2's one interactive control with neither id nor Name (1/54) is a **160×28 px
  ComboBox** at (892, 253) with an empty class name — the toolbar quick-search box. HandBrake's
  two (2/45) are a `Button` with bounds `[0,0,0,0]` and a `MenuItem`, which no scenario can act
  on. SC-06's only demand on P1 (not Qt) holds either way.
- **#33's uniqueness test is scoped, not dropped**: it excludes ListItem, DataItem and TreeItem.
  Measured in `keepassxc.json` — each of the four `QListWidget` ListItems carries its `List`
  parent's AutomationId exactly, so item-view children have no `objectName` of their own. With
  galip's #150 table-cell result that is the same rule twice. **This matters beyond #33**: the
  Spy (#24) and the descriptor (#11) cannot treat an AutomationId as unique inside an item view.
- Nit: the evidence table now separates *Elements walked* (106/149/84/109) from *Interactive*
  (54/45/41/79); every share is of the interactive subset.
- omer's addition: under #12/#161 the ADR now names the client — the Spy (#24) and playback
  (#44) will see `-32002` on KeePass 2 windows, so **"snapshot incomplete" is a UI state**, not
  only an agent outcome.

## #21's acceptance criteria are met, and the issue text was edited to say so

Both reviewers answered **yes** to my two questions, so with the user's OK I edited issue #21:

- Criterion 2 now reads *installed in `C:\ayna-pilots\` on every Windows machine used for
  verification (hasan's machine and the weekly-session machine), at the versions pinned in the
  ADR; macOS members work from the committed dumps* — and is **ticked**.
- "Expected output" is corrected from `docs/adr/ADR-001-pilot-apps.md` to
  `memory-bank/decisions/2026-10-31-pilot-apps-and-sample-app-technology.md`.
- Both edits carry a dated `<sub>` note naming whose decision it was, so it is not a silent
  rewrite. **Do this for every migrated issue whose wording predates an ADR** — the board text
  is older than the memory-structure ADR and will contradict it again.

## Next step

1. **Review omer's #179** — it has been waiting and a review is short.
2. **Chase the #169 approvals**, then flip the ADR to `Accepted` in that PR and merge #169
   before #170.
3. Then #180's review, and the ADRs that are `Proposed` although their condition is met.
4. New work after that: **#22** (element under cursor) and **#23** (win32 fallback) now have a
   working `recognition/` to build on.

## Open, not mine to close

- **Three ADRs still say `Proposed` although their condition is met**:
  `2026-10-27-step-schema-v0` (#13), `2026-10-31-element-descriptor-v0` (#11 closed with three
  approvals, PR #175) and — once #169 is approved — D1 itself. Someone has to flip each.
- **`minLength: 1` cannot say "not only spaces"** in `snapshot.schema.json` and
  `element.schema.json`: a Java or TypeScript producer could write `"   "` and be valid. My
  recommendation is a non-whitespace `pattern` on every string property in both, one PR bumping
  both to 0.2, **after** #15 and #24 land against 0.1.
- `schemas/AGENTS.md` names only the step schema's tests, in `ai/`; the element and snapshot
  schemas are tested in `agent/`. It needs a line, but it is an `AGENTS.md`, so **ask the user**.
- **Only Python 3.13 exists on this machine**, while every module declares `>=3.11`. A green
  local run is **not** evidence that the version floor holds — see `learnings.md` 2026-11-01.
- Galip owes a decision from my #173 review: whether a model server that is **not running**
  should keep arriving as a 504 `timeout` on Windows (a closed loopback port times out here
  instead of being refused). Plus two one-liners: #173's IPv6 listen address, #176's explicit
  LF newline. From my #166 review he also owes the one-sided `dpi` fallback decision in the
  healing scorer; omer's half of that is settled by the proposal-schema 0.2 ADR (`dpi` on
  Element) and he takes it into #25.
- Small follow-up branch, not started: the pre-ADR ownership tables in
  `docs/working-agreement.md` §1 and `docs/README.md` (galip's #19 note), and the
  `requirements.txt` mentions in `tasks/8-*.md` / `tasks/9-*.md` (omer's #122 note).
- **PR #138** is empty (0 files) because #143 carried its content to `main`; it should be
  **closed, not merged**. Side effect: `docs/requirements-workshop.md` is on `main` with §7
  still the empty template, tracked by #19 — galip must fill it.
- **Branch `hasan/2209a-application`**: created from `main`, no commits, not created by me.
  Worth finding out whose it is before someone builds on it.
- **`copilot-swe-agent[bot]`** has pushed merge commits to branches of mine (`d261faa` on
  `hasan/161-winforms-walk`, co-authored by omer) and once left a literal `<<<<<<< HEAD` marker
  in `memory-bank/decisions/README.md` that reached `main`; #160 removed it. **Check that file
  whenever that bot touches a branch of mine**, and ask omer what the bot is for.
- Unverified, one weekly-session check: a **second monitor at another scaling**. Every snapshot
  number so far is from one 120-DPI display, so `dpi` has only ever been 120 and no snapshot has
  had negative `bounds`.
- #21's old criterion-2 problem is **closed** by the edit above. The KeePassXC auto-lock check
  stays pending in `tasks/21-pilot-apps-decision.md` and is only needed before KeePassXC is
  promoted to pilot 3.
- Inbox: handled up to 2026-10-31. Do not delete the handled lines yet — PRs #150 and #126 still
  add lines to that file and `merge=union` would bring deleted ones back.

## Environment, so it is not re-derived

`agent/.venv` exists (`pip install -e ".[dev]"`); `eval` installs with
`.venv/Scripts/python.exe -m pip install -e "eval[dev]"` from the repo root (omer replaced
`eval/apps/trial/requirements.txt` in #122). `client/node_modules` is installed. KeePass 2's demo
database: `%USERPROFILE%\OneDrive\Belgeler\Database.kdbx`, password `ayna-demo`; the #161 driver
uses `C:\ayna-pilots\ayna-demo.kdbx` instead.
