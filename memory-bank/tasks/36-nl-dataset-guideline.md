# #36 Turkish NL dataset guideline + first 40 pairs (with Hasan)

- Issue: https://github.com/galipdg/AYNA/issues/36
- Owner: galip (with hasan) · Branch: `galip/36-nl-dataset-guideline` (stacked on `galip/13-step-schema`, PR #134)
- Started: 2026-10-27 · Last update: 2026-10-27

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

## Status
- [x] Branch, task note, board In progress
- [x] `guideline.md`, `pair.schema.json`, `objects.schema.json`, `check_pairs.py`, `objects/trial.json`, 12 trial pairs (login 6, checkpoint 3, wait 3; 5/3/3 styles)
- [x] `ai/tests/test_nl_dataset.py`: 34 tests (repo dataset clean, 23 rule mutations each caught, held-out freeze/edit/overlap); ai suite 78 passed, ruff clean
- [x] Live smoke run of the #37 generator on the trial pairs (below)
- [ ] PR (`Refs #36`), reviews hasan + omer, inbox note to hasan
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

## Handoff
- The trial pairs were generated with a scratch script; edit `pairs.jsonl` directly from now on, one JSON object per line, `ensure_ascii=False`.
- `check_pairs.py --min-styles 0` while a type is still being filled; the committed set must pass with the default 3.
- The section numbers of `guideline.md` (3, 5, 6.1–6.6) are cited by `pairs.jsonl` notes, the schemas and the checker; renumbering means updating them.

## Outcome (fill when the issue closes)
