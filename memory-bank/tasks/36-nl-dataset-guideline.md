# #36 Turkish NL dataset guideline + first 40 pairs (with Hasan)

- Issue: https://github.com/galipdg/AYNA/issues/36
- Owner: galip (with hasan) · Branch: `galip/36-nl-dataset-guideline` (stacked on `galip/13-step-schema`, PR #134)
- Started: 2026-10-27 · Last update: 2026-10-31

## Approach
Everything that does not need the sample app is done now; the 40 sample-app pairs are a fill-in job once #33 (which waits on D1 #21) lands. `eval/nl/guideline.md` holds the rules (use and held-out policy, record format, scenario types, Turkish vocabulary, styles, gold labelling, sample-app procedure, outsider procedure and brief for #57, reviewer checklist). The format is formal: `eval/nl/pair.schema.json` (gold refs `urn:ayna:schema:step`) and `eval/nl/objects.schema.json`. `eval/nl/check_pairs.py` validates both schemas plus the rules a schema cannot express (see its docstring). `eval/nl/pairs.jsonl` holds 12 worked pairs on the trial app (#9) with real AutomationIds in `eval/nl/objects/trial.json`; they do not count toward the 40.

## Decisions (small, local to this task)
- 2026-10-27 — Checker is a script next to the data (`eval/nl/check_pairs.py`, only `jsonschema`), run in CI by `ai/tests/test_nl_dataset.py` (imports it by path) — `eval/` has no pyproject or CI job yet (#122); move the test to `eval/` when it has one. ai's ruff does not cover `eval/nl/`; I ran `ruff check` / `ruff format --check` on it by hand.
- 2026-10-27 — Pair format: `id, app, appVersion, scenarioType, scenario, style, tags?, origin, author, text, gold, notes?`; camelCase like the other contracts. `gold` is a full step document (not `expected`, which the #37 CLI reads as a keyword list). Field `scenario` groups phrasing variants; variants must have identical gold (checked).
- 2026-10-27 — "≥ 3 phrasing variants per scenario type" = ≥ 3 distinct `style` values per (app, scenarioType); styles are a closed enum (imperative, polite, descriptive, terse, stepwise) so RQ3 can break accuracy down by style. Tags (implicitTarget, informal, reordered) are optional, closed.
- 2026-10-27 — Eight scenario types: six by sample-app screen (#33, #34: login, form, listSearch, settings, dialog, wizard) plus `checkpoint` (only Verify) and `wait` (has a Wait), assigned by a first-match rule that the checker enforces. Quota for #36: 5 pairs × 8 types, ≥ 2 scenarios and ≥ 3 styles per type.
- 2026-10-27 — Held-out policy decided here for #57: the 30 pairs are *moved* to `heldout.jsonl`, split by scenario (no paraphrase leakage), frozen with `heldout.sha256` in the same commit; the checker fails on a changed hash or a scenario on both sides. Only `app: "sample"` pairs count toward 40/100.
- 2026-10-27 — Gold follows the text, not the app; values must appear in the text (checker folds case and diacritics); Select values must be the object's `items`. Keyword/property vs control type table (guideline 6.3) is enforced, mainly to stop `value` checks on labels.
- 2026-10-27 — Object list per app (`objects/<app>.json`): `automationId`, `controlType`, Turkish `description`, `items`. Richer than the #37 CLI's `{name: description}`; converting is one line (`{n: o["description"]}`). Trial `appVersion` = `5e23d15` (commit of `app.py`), since the app shows no version. Only the five controls checked by `test_uia.py` plus the window (README) are listed; the two text labels are left out (their AutomationIds are not verified on Windows).
- 2026-10-31 — **Quoting in team pairs** (hasan, #145 review §4): his exact ask is "make quoting required for team-written pairs whenever the value's last syllable could read as a suffix, and restrict the bare-stripping rule to outsider texts", checkable by review. Guideline §4.4 now says exactly that. The checker enforces the scriptable half for `origin: team` (`bare-suffix`): every value/expected must occur at least once with no letter or digit glued to either end, i.e. no suffix stripped from a bare value (an apostrophe or closing quote is a boundary, so *Ankara'yı* and *"Kalite Güvence"yi* pass). Not chosen: "every team value quoted, always". It is scriptable, but it would rewrite 9 of the 12 trial texts (bare `admin`, `yanlis123`). It would also make team texts systematically easier than outsider texts, which skews RQ3, and remove quoting as a variant dimension (§5). The "could read as a suffix" half (*Kalite Güvencesi* written whole) cannot be told apart by a script and stays a review item (§9). All 12 trial pairs pass unchanged. Outsider texts are exempt (kept as written; the reading goes in `notes`).
- 2026-10-31 — **Check boxes** (hasan, #145 review §4, "the check box rows teach the model to ignore negation"; it is the `settings` item: "discovered when #40 runs the `settings` pairs"): new §6.8. Click toggles, so only the form that changes the box from its start state (app default, or the state an earlier step left) is a pair; the other form is out of scope (§6.7) and dropped for outsiders. Every pair with a Click on a CheckBox states `start state: unchecked|checked` in `notes`; the checker requires the phrase (`start-state`, regex in `check_pairs.START_STATE`), the reviewer checks it is right. No sample-app objects invented: the rule uses the trial app's real *Remember me* box as its example, and no pair was added (#150 rewrites every `pairs.jsonl` line for v0.2, and an added line would conflict). A `Check`/`Uncheck` keyword (or Click with an end state) is a schema question after v0.2, not raised on #147 from here.
- 2026-10-31 — **Closed lists**: `style`, `tags`, `scenarioType` were already closed enums in `pair.schema.json` (2026-10-27). Added `test_closed_lists_in_the_pair_schema_match_the_guideline`, which parses guideline §3 and §5 and fails when the schema and the guideline drift apart, plus `unknown-style` and `unknown-tag` mutations.
- 2026-10-31 — Small items from the same review folded in: §3 caveat that per-type accuracy is not per-screen accuracy (hasan kept the eight-type enum on the condition of this sentence); *kaydı sil* in the implicit actions (Click, not Type `""`); §9 double-labelling on 20 **outsider** pairs (team pairs agree by construction).

## Status
- [x] Branch, task note, board In progress
- [x] `guideline.md`, `pair.schema.json`, `objects.schema.json`, `check_pairs.py`, `objects/trial.json`, 12 trial pairs (login 6, checkpoint 3, wait 3; 5/3/3 styles)
- [x] `ai/tests/test_nl_dataset.py`: 34 tests (repo dataset clean, 23 rule mutations each caught, held-out freeze/edit/overlap); ai suite 78 passed, ruff clean
- [x] Live smoke run of the #37 generator on the trial pairs (below)
- [x] PR https://github.com/galipdg/AYNA/pull/145 opened 2026-10-27 (`Refs #36`, stacked on #134, merge after it), reviewers hasan + omer; request in hasan's inbox
- [x] Review follow-ups from #145 (2026-10-31, branch `galip/36-dataset-review-followups`): §4.4 quoting + `bare-suffix`, §6.8 check boxes + `start-state`, closed-list sync test, §3 caveat, §9 outsider double-labelling; `test_nl_dataset.py` 64 tests; ai suite 385 passed; `check_pairs.py` ruff-clean (by hand)
- [ ] Criterion 2 (40 pairs) and 3 (≥ 3 variants per type on them) — wait on #33 ← #21
- Next step: when #33 lands, get `eval/nl/objects/sample.json` from hasan, then write the 40 sample pairs by guideline §7 (5 per type, half each), run `check_pairs.py`, and tick criteria 2–3; merge after #134.

## Live smoke run (2026-10-27, not an experiment)
#37's generator from PR #142 (`git show` into a scratch dir, not merged), on the 12 trial pairs, objects as `{name: description}`, MacBook M2 16 GB shared with other agents (load ~6), Ollama 0.40.11, default settings (schema format, temperature 0, seed 42). Exact match = all generated steps equal the gold steps.

| Model | Valid | Keyword sequence | Exact match | Steps equal by position | p50 / p95 latency |
|---|---|---|---|---|---|
| qwen3:8b | 12/12 | 9/12 | **3/12** | 35/51 | 13.5 / 16.9 s |
| gemma4:e4b-it-qat | 12/12 | 10/12 | **9/12** | 47/51 | 11.9 / 27.9 s |

- qwen3 checks the status label with `value` instead of `name` in 6 pairs (every "durum etiketi … boş / yazmalı"); the description says "etiket" but not the control type. Supports #37's handoff note: give the model the control type (or a property hint) per object (#58).
- Both models drop the Click in the `reordered` pair (*Login'e basmadan önce … yaz*): the tag marks a real difficulty.
- qwen3 adds Clicks on input fields (with `timeoutMs` 5000) in the `informal` terse pair, and a Click on the window in the `implicitTarget` pair. gemma4 drops one `timeoutMs` and invents a label text for *durum boş*.
- 12 sentences on one screen say little about RQ3; the numbers only show the format works end to end.

## Manual checks
- none: no UI. The trial objects' AutomationIds come from hasan's Windows-verified `test_uia.py` (#9), not re-checked here.

## Open issues
- Schema v0 cannot select or check grid rows (#37 finding). `listSearch` pairs can only Select in a List/ComboBox; asked hasan whether the sample app's list screen can offer one (inbox). A v0.2 row/cell check is a separate issue to raise after #134.
- `ai/ayna_ai/generate.py` (#37) reads `--objects` as `{name: description}`; to run it on `eval/nl/` it needs the one-line conversion or an option to read `objects/<app>.json` — do it in #37's criterion-1 run, not here.
- When #122 gives `eval/` a pyproject and CI job, move `test_nl_dataset.py` there and lint `eval/nl/` in CI.
- Open from hasan's #145 review (2026-10-31), not done in the follow-up PR. **Grid note**: a Qt table's UIA Name is `""`, so `Verify <grid> name contains …` always fails, not merely checks the wrong thing; belongs to #150's §3/§6.7 rewrite, which edits that paragraph. **Three-way *seç* rule** (Click / Select / SelectRow by control type): after #150. **statusLabel note** in the trial pairs (its Name is `''` at start): touches `pairs.jsonl`, which #150 rewrites, so do it after #150 merges. **§8 outsider procedure**: written, irrevocable consent kept outside the repo; HAVELSAN testers only after the advisor and contact agree; taking the "çift tıklama … kullanmayın" line off the brief so the drop rate is a finding. Hasan collects and offered to word the consent sentence. The brief line is galip's methodological call (fewer drops vs. an unprimed drop rate), so decide it before #57 starts. **Check/Uncheck keyword**: a schema question after v0.2.

## Handoff
- The trial pairs were generated with a scratch script; edit `pairs.jsonl` directly from now on, one JSON object per line, `ensure_ascii=False`.
- `check_pairs.py --min-styles 0` while a type is still being filled; the committed set must pass with the default 3.
- The section numbers of `guideline.md` (3, 4.4, 5, 6.1–6.8) are cited by `pairs.jsonl` notes, the schemas and the checker; renumbering means updating them.

## Outcome (fill when the issue closes)
