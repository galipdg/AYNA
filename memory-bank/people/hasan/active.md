# Active — Hasan Berk Yanıkkaya (`hasan`)

Only hasan's agent edits this file. Overwrite it at every session end.

- Last update: 2026-10-29
- Current issue: none in progress. #6 is done and waiting for review as PR #159.
- Branch: `hasan/6-uia-dumps` (PR #159 open, `Closes #6`)
- Next step: open the two issues promised in today's reviews (see "Owed to teammates" below),
  then pick up #122 (`eval/` pyproject + ruff) — omer's CI job waits on it and it also carries
  the `docs/working-agreement.md` §1 / `docs/README.md` ownership fix galip asked for.

## What happened this session

Cleared the whole review queue: **all 11 PRs reviewed** (#135, #138, #141–#146, #150, #151, #157).
Approved: #141, #142, #144, #145, #146, #151. Left as comments with specific asks: #135, #138,
#143, #150, #157. Nothing is waiting on me for review any more.

Reviews were backed by measurements taken on this machine rather than opinion, which is what made
them worth the time:

- **Qt grid/list probe** (for #150): answered all four of galip's UIA questions empirically and
  found two defects in the step schema v0.2 — the "ValuePattern first" rule reads `''` for every
  Qt cell (text is in `Name`), and a `cell` check can never be valid against a list, because it
  requires a `column` and a list has no headers. Also found that every descendant of a Qt table
  carries the table's own AutomationId.
- **Scorer probe** (for #141): a *wrong* toolbar button scores **0.800** against a Win32 target
  with no id and no Name, and the score is not comparable across targets (a "shares only
  controlType" candidate scores 1.000 / 0.333 / 0.158 for a 1 / 3 / 11-property target) → #73's
  minimum score must be derived per target, not a constant. The location cut-off is in physical
  pixels, so the same move scores 0.36 at 100% and 0.20 at 125%.
- **Trial app verification** (for #145): all six objects in `eval/nl/objects/trial.json` confirmed
  live against the running app — galip had this marked "not verified".
- **WinForms read cost** (for #143/#138): plain property reads 2.79 ms/element and the ten pattern
  probes 1.56 ms/element, so finding 7's pattern-probe hypothesis does **not** hold and the
  278.5 s is tied to that window state. Corrected finding 7 in `eval/spikes/uia-dump.md` and
  posted the correction on #143 and #138, because I had overstated it in both reviews.
- `ElementFromPoint` is ~5 ms, so NFR-01's 300 ms is comfortable.

## Sign-offs I gave (binding; others are building on them)

- **NFR-02** (2 s snapshot): confirmed **only** scoped to the sample app, with a sentence saying so.
- **NFR-04** (500 ms/step): confirmed as a target, if it says what it measures and exempts the
  polling checkpoints that #150 introduces.
- **NFR-05** (10 000 ms default): confirmed; asked that `timeoutMs: 0` be documented as legal.
- **TBD-5**: confirmed, **plus a third failure state** — "the search ran out of budget" must not be
  "element not found", or healing ranks candidates from an incomplete tree. Raised on #143, #138,
  #144 and #157; whichever document decides it, the others follow.
- **TBD-6** (stop after "repair proposed"): confirmed, accepting that measuring healing recall
  over N broken elements then costs N runs.
- **RQ2** (#69): confirmed, with an app-state reset between runs, "same result" meaning per-step,
  and the detection limit stated (10 runs catch 26%-per-run flakiness at 95%, only 40% of a 5% one).
- **RQ1** (#64): **refused as defined** — "identified uniquely from its descriptor" is vacuous
  because `parentPath` + `siblingIndex` identify everything. Proposed two numbers (stable
  properties only, then with positional fallback) and the `uia_dump.py` interactive set as the
  population.
- **CLI runner exit codes** (#61): 0 all passed and delivered · 1 a test failed or proposed a
  repair · 2 operational failure even if every test passed. UC-14 in #138 contradicts this.
- **Key naming**: camelCase at every contract boundary, snake_case only inside Python modules.
  The #11 descriptor is mine to align.
- **`parentPath`**: programmatic ControlType names joined by `/`, never localised ones — we test
  Turkish UIs and a localised path would zero that property across machines.

## Owed to teammates

1. **Open two issues** I promised in reviews: (a) reproduce the #6 KeePass 2 window state and
   bisect the 278.5 s walk; (b) install Ollama on this Windows machine and measure #142/#146's
   batch — every LLM number we have is from galip's M2, the service's p95 is already 25.3 s there
   and its 30 s deadline fires, and Windows is the delivery platform.
2. **#122** (`eval/` pyproject + ruff) — omer's CI job waits on it. It will also lint
   `eval/nl/check_pairs.py`; I told galip I would cover all of `eval/` unless he objects.
3. **`docs/working-agreement.md` §1 and `docs/README.md`** still show pre-*windows-work-to-hasan*
   ownership (galip flagged it in #138). Mine to fix; said I would do it alongside #122.
4. **#33 (sample app)**: its grid must set `setSelectionBehavior(SelectRows)` or #150's SelectRow
   keyword is dishonest, and it needs a reset-to-baseline hook for RQ2.
5. **Outsider NL pairs (#57, §8 of the guideline)**: I collect them. Consent must be written and
   obtained before anything enters git (history cannot be rewritten, so a withdrawal cannot be
   honoured afterwards), HAVELSAN testers need clearing with the advisor first, and I argued for
   dropping the "don't use double-click / fixed waits" line from the brief so the drop rate stays
   a finding. Cannot start until #33 exists.
6. **Check-box toggle gap**: *işaretle* and *işaretini kaldır* both map to `Click`, so the dataset
   would teach the model to ignore negation, and v0 cannot express "make sure it is checked".
   Raised on #145; worth deciding in #147 while the schema is open.

## Open questions

- #9 / PR #116 is still open awaiting a review, and #2's last criterion ("all three members merged
  one test PR") waits on it. Ask omer whether #9's PR counts for #2.
- Inbox: omer's #3 CI-skeleton review; omer's two #8 criteria that disagree between the issue and
  PR #121 (was the advisor summary sent?) — I asked galip on #138 to settle it in §7 of the
  workshop doc, since the 27 Oct meeting is the likely answer and §7 is still empty.
- #138 cannot merge until galip fills §7; #143, #150 and #157 are waiting on my asks.
