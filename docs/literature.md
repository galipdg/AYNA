# Literature review

Annotated sources behind AYNA's design and research questions. Section 1 (#10) covers test fragility, locators and self-healing; section 2 (#20) covers language models in GUI testing and decision models. Each entry gives the finding and what it means for AYNA. Full citations use the numbering of the project plan ("AYNA – 14-Week Project Plan", References).

Last update: 2026-10-27

## Section 1 — Fragility, locators, self-healing (#10)

### Assignment

Each member annotates at least three sources (#10 acceptance criteria). The split follows code ownership: whoever builds the part a source informs annotates it. Swap freely; update this table when you do.

| Plan ref | Source | Theme | Annotated by | Status |
|---|---|---|---|---|
| [3] | Hammoudi et al., ICST 2016 | Record/replay fragility | omer | done |
| [4] | Leotta et al., WCRE 2013 | Record/replay fragility | omer | done |
| [23] | Healenium | Test repair / self-healing | omer | done |
| [7] | Similo (Nass et al., TOSEM 2023) | Robust locators | galip | done |
| [10] | WATER (Choudhary et al., 2011) | Test repair / self-healing | galip | done |
| [11] | Vista (Stocco et al., ESEC/FSE 2018) | Test repair / self-healing | galip | done |
| [5] | ROBULA+ (Leotta et al., JSEP 2016) | Robust locators | hasan | todo |
| [6] | Contextual clues (Yandrapally et al., ISSTA 2014) | Robust locators | hasan | todo |
| [12] | Luo et al., FSE 2014 | Flaky tests | hasan | todo |
| [8] | Sikuli (Yeh et al., UIST 2009) | Visual GUI testing | hasan | todo |
| [9] | Alégroth et al., IST 2016 | Visual GUI testing | hasan | todo |

Entry format: **Citation** · **Finding** (what the source shows, with its numbers) · **What it means for AYNA** (design consequence, linked to a brief item, RQ or ADR) · **Source checked** (what was actually read).

### 1.1 Record/replay fragility

#### [3] Hammoudi, Rothermel, Tonella — Why do record/replay tests of web applications break?

- **Citation:** M. Hammoudi, G. Rothermel, P. Tonella, "Why do record/replay tests of web applications break?," IEEE ICST, 2016.
- **Finding:** Selenium IDE suites were replayed across 300 versions of 5 open-source web apps, giving 722 test breakages; 3 more apps (153 versions, 343 breakages) validated the taxonomy without changes. Breakages fall into five causes: locators, values and actions, page reloading, user session times, popup boxes. Locators caused over 73% of breakages, and attribute-based locators (id, name) alone over 50% of all breakages. The authors note this does not prove attribute locators are worse, since counts are not normalised by how often each strategy is used, and conclude that repairing locator breakages pays off most.
- **What it means for AYNA:**
  - Element identification is the main maintenance risk, so it is AYNA's core: multi-property descriptors with primary and fallback properties in the object repository (brief items 1–2) and explainable self-healing (C2).
  - Even "stable" attributes break. On the desktop the analogues are `AutomationId` and `Name`, so a descriptor must not rely on one property; this is the motivation for RQ4 / H1 (weighted vs single-property healing).
  - Two of the five causes (page reloading, popups) are timing and window-state problems, which smart-wait playback (brief item 4) and RQ2 address.
  - The five-cause taxonomy can label the breakages in our controlled UI-change versions (C4), so our numbers are comparable with this study.
  - Gap: web DOM and Selenium IDE only; no equivalent study exists for the Windows UI Automation tree.
- **Source checked:** paper summary (A. Colyer, *the morning paper*, 2016, linked from the plan); numbers above are quoted from it.

#### [4] Leotta, Clerissi, Ricca, Tonella — Capture-replay vs. programmable web testing

- **Citation:** M. Leotta, D. Clerissi, F. Ricca, P. Tonella, "Capture-replay vs. programmable web testing: An empirical assessment during test case evolution," WCRE, pp. 272–281, 2013. DOI 10.1109/WCRE.2013.6671302.
- **Finding:** On six open-source web apps, suites were built twice — capture-replay (Selenium IDE) and programmable (Selenium WebDriver) — and maintained across a new release. Programmable suites took 32–112% more time to develop but 16–51% less time to maintain; in most cases their cumulative cost fell below capture-replay after one to three releases.
- **What it means for AYNA:**
  - Recorded tests are cheap to create and expensive to keep; non-programmers lose that trade-off after a few releases. A codeless tool has to give recorded tests the maintainability of programmed ones without asking for code.
  - Our interpretation: the object repository plays the role a shared locator layer plays in programmable suites. Steps refer to logical names (brief item 2), so a UI change is fixed once in the repository, not in every test. C3 (change-impact analysis from the graph) then shows which tests a change touches.
  - Evaluation idea: measure repair effort per UI-change version (C4) with and without the repository and healing, in the spirit of this cost comparison.
  - Gap: web only; no codeless or self-healing condition was compared.
- **Source checked:** abstract only, as indexed by web search (2026-10-26). The full PDF (https://sepl.dibris.unige.it/publications/2013-leotta-WCRE.pdf) could not be retrieved: the server refused the connection. Per-application figures and the method are not verified; read the PDF before citing details in the RS.

### 1.2 Robust locators

#### [5] ROBULA+ — *to be annotated by hasan*

#### [6] Contextual clues — *to be annotated by hasan*

#### [7] Nass, Alégroth, Feldt, Leotta, Ricca — Similo: similarity-based web element localization

- **Citation:** M. Nass, E. Alégroth, R. Feldt, M. Leotta, F. Ricca, "Similarity-based web element localization for robust test automation," ACM TOSEM, vol. 32, no. 3, art. 75, 2023. DOI 10.1145/3571855.
- **Finding:** Similo stores 14 locator parameters of the target element and scores every candidate on the new page; the candidate with the highest weighted sum wins. Each parameter has its own comparison: exact match (case-insensitive) for Tag, Id, Name and IsButton; normalised Levenshtein similarity for Class, HRef, Alt, absolute and id-relative XPath and visible text; shared-word ratio for the texts of neighbouring elements; normalised distance for location (zero beyond 100 px), area and shape. Weights were set by hand: 1.5 for the parameters an earlier study (COLOR) found stable — Tag, Id, Name, visible text, neighbour texts — and 0.5 for the rest. On 801 target elements from the home pages of 48 top websites, comparing a December 2020 version with an Internet Archive copy 12–60 months older, Similo failed to locate the right element in 91 cases (11%). The baseline, Leotta's multi-locator (voting over five XPath locators) at its theoretical best, failed in 214 (27%); the best single locator (ROBULA+ [5]) failed in 39%, absolute XPath in 83%. Scoring took about 4 ms per element. The authors name two weaknesses: without a threshold Similo always returns *some* element, even when the target is missing or not loaded yet; and the weights are untuned. Desktop and mobile apps (e.g. "the Windows accessibility framework") are named as future work, not evaluated.
- **What it means for AYNA:**
  - It is the template for C2's scorer (#49) and for the descriptor (#11): keep several UI Automation properties per element and give each a comparison that suits it. A first mapping: Id → `AutomationId`, Name → `Name`, Tag → `ControlType`, Class → `ClassName`, XPath → path in the UIA tree, visible text → `Name` / `Value`, neighbour texts → nearby label controls, location / area / shape → `BoundingRectangle` (normalised for DPI scaling).
  - Per-property similarity × weight is exactly the explanation C2 promises; the proposal screen (#75) can show these terms as they are.
  - "Always returns something" is why AYNA needs a minimum score and the approval gate (decision 2026-10-20 approval-gated self-healing): below the threshold there is no proposal, and healing runs only after the smart wait has given up (brief item 4), not while the window is still loading.
  - Similo's hand-set weights are a ready baseline for RQ4 / H1 (weighted vs `AutomationId` only); learning the weights is the paper's own future work and fits the calibrated decision layer (#103).
  - Exact match on Id is fragile for Qt, whose `AutomationId` is a dotted path that changes when an ancestor is renamed (learnings 2026-10-25); a string similarity on that property is worth comparing.
  - Gap: web DOM only. Its 4 ms assumes all properties are in memory; reading UIA properties is a cross-process call, so score against a window snapshot (#12) instead of querying each candidate live.
- **Source checked:** full published paper (Chalmers research repository copy), sections 3–7 and 9, Tables 1 and 5 (2026-10-27).

### 1.3 Visual GUI testing

#### [8] Sikuli — *to be annotated by hasan*

#### [9] Alégroth et al. — *to be annotated by hasan*

### 1.4 Test repair / self-healing

#### [10] Choudhary, Zhao, Versee, Orso — WATER: Web Application TEst Repair

- **Citation:** S. R. Choudhary, D. Zhao, H. Versee, A. Orso, "WATER: Web application test repair," Proc. 1st Int. Workshop on End-to-End Test Script Engineering (ETSE, with ISSTA), pp. 24–29, 2011. DOI 10.1145/2002931.2002935.
- **Finding:** WATER uses differential testing: it runs a broken Selenium test on the old version (where it passes) and on the new one (where it fails), keeps both DOMs and the failure message, generates repair candidates, reruns the test with each candidate, discards those that still fail and suggests the rest to the tester. Broken locators are repaired by finding the element in the new DOM through its id, XPath, class, link text and name; failing assertions by replacing the expected value with the actual one or negating the check; new form fields by filling in random values. Subjects were Joomla (42 Selenium tests), Ofbiz (16) and 180 of 5,123 CoScripter scripts run daily against live sites. On Joomla and Ofbiz the suggestions matched the fixes developers later made, with 1–3 suggestions per broken test; on the live-site scripts link-text changes were fixed but with up to 285 suggestions, and form changes were not fixed. In Vista's later comparison [11], WATER's locator heuristics repaired 420 of 733 breakages (57%) and detected none of the 38 cases where a locator silently selected the wrong element.
- **What it means for AYNA:**
  - The loop behind C2 already appears here: keep what the last passing run saw, compare it with the failing run, propose candidates, let a person decide. AYNA's "last passing run" is the window snapshot (#12) and the comparison is #42.
  - Rerunning the test with a candidate is a cheap check before a proposal is shown — as a separate "verify proposal" action, never inside the CI run.
  - Its assertion "repair" (expected := actual) is exactly how silent healing hides real bugs. AYNA heals only element descriptors; a changed checkpoint value stays a failure for a person to judge (RQ5 / H3).
  - Up to 285 unranked suggestions are useless to a tester, so AYNA ranks candidates and shows the top few with their scores (Similo-style, [7]).
  - A property-only matcher cannot notice that the element it found is the wrong one (0 of 38 in Vista's study). AYNA's healing shares this blind spot; checkpoints and the D3 visual-fallback decision (#65) are the guards.
  - Gap: web only, small workshop study, no ranking or explanation, no desktop support.
- **Source checked:** the authors' talk slides (shauvik.com/public/pubs/WATER.pptx, 23 slides) and the descriptions in Vista [11] §5 and Similo [7] §3.1 (2026-10-27). The paper itself could not be read: the ACM Digital Library returned 403 and the old Georgia Tech copy is gone. Read the paper before citing details in the RS.

#### [11] Stocco, Yandrapally, Mesbah — Vista: visual web test repair

- **Citation:** A. Stocco, R. Yandrapally, A. Mesbah, "Visual web test repair," ESEC/FSE, pp. 503–514, 2018. DOI 10.1145/3236024.3236063.
- **Finding:** The authors classified 733 breakages in 2,672 Selenium tests over 86 releases of four open-source web apps. 695 were *non-selections* (the locator finds nothing; the element is on the same page, moved to a neighbouring page, or removed) and 38 *mis-selections* (the locator finds a different element; two thirds broke at that step, one third later). 12% of the tests broke at least once, and about 80% of those broke more than once. Vista records, for every step of a passing run, a screenshot and the element's bounding box. On the new version it checks each step before running it: if the DOM locator finds nothing, it looks for the element's image on the page (SIFT and FAST key-points, then template matching with a 0.99 threshold) and maps the match back to the DOM element at that position; if that fails, it crawls neighbouring pages, and otherwise suggests deleting the step. If the DOM locator finds an element that differs from the visual match, it reports a mis-selection. The tester confirms, discards or replaces each suggestion. Vista repaired 592/733 breakages (81%) against 420 (57%) for WATER's heuristics [10], and 80% of mis-selections against none. WATER won only in 3 cases, where the DOM stayed the same but the look changed. Recording the visual trace made the suites 3.6× slower (+38 min in total); unrepaired cases included timing problems (elements not shown yet) and buttons that turned into icons.
- **What it means for AYNA:**
  - The non-/mis-selection split maps onto AYNA. A descriptor that finds nothing leads to a healing proposal; a descriptor that finds the *wrong* element is the dangerous case, and healing triggered only by "not found" misses it, as WATER did. A cheap guard: before acting, score the found element against the stored snapshot (#12) and stop with a proposal if the score is low, even when the primary property matched.
  - Playback already takes a screenshot per step (brief item 5). Storing the element's crop and bounds from the last passing run would give D3 (#65, visual fallback or not) real data, without committing to a visual matcher now. The 3.6× tracing cost is the price to weigh.
  - The tester confirms each repair, so Vista is a precedent for AYNA's approval gate (decision 2026-10-20), not a contrast. AYNA differs in being desktop/UIA, explaining each proposal per property (C2) and showing which tests a change affects (C3).
  - Its timing failures support healing only after the smart wait gives up (brief item 4, RQ2).
  - The taxonomy (same page / neighbouring page / removed / mis-selection) can label the breakages in our UI-change versions (C4) next to Hammoudi's causes [3].
  - Gap: web only; needs a visual trace of a passing run; sensitive to look changes (its three losses to WATER).
- **Source checked:** full paper (authors' PDF, people.ece.ubc.ca/amesbah), sections 2–6 and Tables 1–4 (2026-10-27). The paper gives 86 releases in the abstract and Table 1 but 82 in the introduction; 86 is used here.

#### [23] Healenium (EPAM, open source)

- **Citation:** EPAM, *Healenium*, https://healenium.io, source at https://github.com/healenium (Apache-2.0). Industrial tool, not a peer-reviewed paper.
- **Finding:** Healenium wraps Selenium WebDriver (`SelfHealingDriver`); Appium is also supported. After each successful lookup it stores the locator as a baseline in a PostgreSQL-backed service (`hlm-backend`). When a lookup throws `NoSuchElementException`, it compares the stored element path with the current page (the docs name an "LSC", i.e. longest-common-subsequence, algorithm), ranks candidate locators, and — if the best score is above `score-cap` (e.g. 0.5) — performs the action with the highest-scoring locator and lets the test continue in the same run. It produces a report with the healed locator, a screenshot and a feedback button; an IntelliJ plugin (`hlm-idea`) writes healed locators back into test code. Healing can be switched off globally (`heal-enabled`) or per method (`@DisableHealing`).
- **What it means for AYNA:**
  - It is the closest open-source analogue of C2, and it differs exactly where AYNA's ADR does: Healenium heals mid-run, so a test can pass after the element changed because of a real bug. AYNA records a proposal and never applies it during playback (decision 2026-10-20 approval-gated self-healing; RQ5 / H3).
  - Worth copying: a baseline captured on every successful find, a configurable score threshold, and a report entry per healing with a screenshot. These map onto the healing proposals API (#74) and the approval screen (#75).
  - Where AYNA goes further: Healenium shows one opaque score; AYNA shows per-property contributions so a tester can judge a proposal (C2), and an approve/reject decision updates the repository, not test code, because tests refer to logical names.
  - Gap: web and mobile only (DOM / Appium page source); no Windows desktop support and no closed-network packaging story beyond self-hosted Docker.
- **Source checked:** healenium.io "How Healenium works", the `healenium` and `healenium-web` GitHub READMEs (2026-10-26).

### 1.5 Flaky tests

#### [12] Luo et al. — *to be annotated by hasan*

### Gaps table

Copied from the project plan (section "What has been done"). Keep the two in sync: if an annotation changes a finding or gap, update both. Rows 1–5 are covered in section 1; the LLM row in section 2 (#20); the tool rows in detail in [`tool-matrix.md`](tool-matrix.md) (#18).

| Area | Key work | Finding | Gap for us |
|---|---|---|---|
| Record/replay fragility | Hammoudi et al., ICST 2016 [3]; Leotta et al., WCRE 2013 [4] | Over 70% of 722 studied test breakages came from element locators; record/replay is cheap to create but costly to maintain | Element identification must survive UI changes |
| Robust locators | ROBULA+ [5]; contextual clues [6]; Similo [7] | Similo's weighted multi-attribute similarity cut wrong element matches from 27% to 11% on 48 websites | Studied on the web DOM, not on the desktop UI Automation tree |
| Visual GUI testing | Sikuli [8]; Alégroth et al. [9] | Screenshot matching is technology-independent | Sensitive to resolution, theme and layout changes |
| Test repair / self-healing | WATER [10]; Vista [11]; Healenium [23] | Broken web locators can be repaired automatically | Web-only; fixes are often applied silently, which can hide real bugs |
| Flaky tests | Luo et al., FSE 2014 [12] | Async waits and timing are leading causes of flaky results | Playback needs readiness-based waits, not fixed sleeps |
| LLMs in testing | Survey [14]; GPTDroid [15]; AUITestAgent [16]; UFO [40] | AUITestAgent reached a 77% task completion rate from natural-language requirements on mobile apps; UFO lets a cloud model choose every action in Windows apps (86% of 50 requests, best of three runs) | Mostly mobile/web and cloud models; the one Windows agent decides at run time, which is not repeatable; not closed-network, not in Turkish, not tied to an object repository |
| Commercial tools | TestComplete [21], Ranorex [32], UFT One [31] | Recorder, object repository, keyword tests, reports | Per-user licences; TestComplete's basic plan starts at about $1,210 per user per year [22] |
| Open-source tools | FlaUI [18], pywinauto [33], WinAppDriver [19], Robot Framework [20] | Programmatic UI Automation access; keyword-driven testing | No recorder, repository or self-healing; WinAppDriver's latest stable release is v1.2.1 and it has not had a new stable release for years |

## Section 2 — Language models in GUI testing, decision models (#20)

All entries in this section are by galip and use the entry format of section 1. They are grouped into three themes: language models that drive GUI tests, how a model's output is grounded and constrained, and the decision models and calibration behind the semester-2 decision layer. Section 2.4 explains why AYNA uses the model only while a test is being written.

Numbering: [14]–[16] keep the numbers used in the gaps table; sources first cited here get provisional numbers from [40] up, above every number used so far in this file ([3]–[33]) or in the plan export ([1]–[39]), until the team settles which plan version the numbering follows.

### 2.1 Language models for GUI testing

#### [14] Wang, Huang, Chen, Liu, Wang, Wang — Software testing with large language models: survey, landscape, and vision

- **Citation:** J. Wang, Y. Huang, C. Chen, Z. Liu, S. Wang, Q. Wang, "Software testing with large language models: Survey, landscape, and vision," IEEE Trans. Software Engineering, vol. 50, no. 4, pp. 911–936, 2024. DOI 10.1109/TSE.2024.3368208. arXiv:2307.07221.
- **Finding:** The survey analyses 102 papers (searches from January 2019 to October 2023, starting from 14,623 candidates). By the paper's own table, 20 address unit test generation, 4 test oracles, 23 system test input generation (which includes GUI testing), 7 bug analysis, 13 debugging and 35 program repair (three more carry program repair as a second topic). Mobile apps are the largest group of software under test for input generation (five studies), and no study covers early stages such as test requirements or test plans. ChatGPT is the most used model, then Codex and CodeT5; GPT-4 was already used in 14 studies. 64 studies use only prompt engineering (51 zero-shot, 25 few-shot, 7 chain-of-thought) and 38 pre-train or fine-tune. 67 studies let the model do the whole task and 35 combine it with other techniques (mutation, differential testing, syntax checks, program analysis); the authors conclude that LLMs "are not the sole silver bullet". For mobile GUIs the input is usually the view hierarchy, not a screenshot; no study had used image input yet. Among the open challenges, the authors note that data-privacy concerns lead most organisations to avoid commercial models and prefer open models trained on their own data, which then struggle to match the published results.
- **What it means for AYNA:**
  - AYNA sits in a gap the survey names: test *authoring* from requirements (early-stage work, no studies) for a non-mobile platform. Turkish and desktop do not appear at all.
  - The privacy point is our closed-network requirement seen from industry: local open-weight models (brief, C1) are the expected setting, and published results from cloud models are an upper bound, not a target.
  - "LLM + X" is the pattern of C1: retrieval from the repository, a grammar constraint and a repository validator around the model (#37, #57, #71), not the model alone.
  - The text form of the GUI (view hierarchy) is what GUI studies feed the model; AYNA's equivalent is a compact list of repository objects, not screenshots.
  - Gap: snapshot up to October 2023; agents such as UFO [40] and AUITestAgent [16] came later.
- **Source checked:** arXiv v3: the HTML full text (read in parts) and, in the PDF text, Table 1 and sections 4.3, 5.1–5.4 and 6.2, where the counts above come from; venue, volume and pages from the Crossref record of the DOI (2026-10-27).

#### [15] Liu et al. — GPTDroid: make LLM a testing expert

- **Citation:** Z. Liu, C. Chen, J. Wang, M. Chen, B. Wu, X. Che, D. Wang, Q. Wang, "Make LLM a testing expert: Bringing human-like interaction to mobile GUI testing via functionality-aware decisions," IEEE/ACM ICSE, 2024. arXiv:2310.15780.
- **Finding:** GPTDroid treats Android GUI testing as question answering with ChatGPT (`gpt-3.5-turbo`). At each step it reads the view hierarchy with UIAutomator and turns it into a prompt: app name and activity list, current activity, widgets by text or resource-id with an upper/lower position, and each widget's text, hint, id, class and neighbouring text. A few-shot output template makes the answer an executable action. If the named widget is not on the page, a feedback prompt says so and asks the model to choose again. A "functionality-aware memory" adds the last 5 pages and actions with visit counts and asks the model which function it is testing. On 93 apps (20 from the Themis benchmark, 73 from Google Play) with 143 crash bugs, 60 minutes per tool per app, each tool run three times with the best run kept, it reached 75% activity and 66% code coverage, against 57% activity coverage for the best of 15 baselines (Ape with QTypist), and found 95 bugs against 66 (Stoat with Toller). Replacing the extracted GUI context with the raw view hierarchy dropped activity coverage from 0.75 to 0.17; removing the memory dropped it to 0.34. On 223 further apps it found 53 new crash bugs, 35 of them confirmed or fixed. Among the reasons for uncovered screens, the authors name widgets without meaningful text or resource-id.
- **What it means for AYNA:**
  - Structured GUI context matters more than anything else in their ablation (0.75 vs 0.17). AYNA's NL prompt should carry a short, curated list of repository objects (logical name, `ControlType`, `Name`, nearest label) for the current screen, not a raw UIA dump. This supports H2 and the retrieval design (#57); our spike also found that prompt length dominates latency on a laptop (#7, finding 6).
  - "There is no such widget, please reselect" is a run-time version of AYNA's repository validator. AYNA does the same check at authoring time: a generated step whose target is not in the repository is rejected and can be regenerated once with the error, before a person sees it (#71).
  - Widgets without meaningful text or id defeat the model just as they defeat locators, which is one more argument for the testability guideline (#94: `AutomationId`, accessible names).
  - Its goal is exploration with a crash oracle, and it reports the best of three runs: two runs take different paths. That is acceptable for bug hunting and not for regression playback (section 2.4).
  - Gap: Android only, crash bugs only, cloud model, English.
- **Source checked:** full paper (arXiv PDF of the ICSE 2024 version, 12 pages; converted to text locally because WebFetch could not read the PDF), sections 2–5 and Tables 5–7 (2026-10-27).

#### [16] Hu et al. — AUITestAgent: requirements-oriented GUI function testing

- **Citation:** Y. Hu, X. Wang, Y. Wang, Y. Zhang, S. Guo, C. Chen, X. Wang, Y. Zhou, "AUITestAgent: Automatic requirements oriented GUI function testing," arXiv:2407.09018, 2024 (preprint).
- **Finding:** AUITestAgent takes a natural-language test requirement for a mobile app (interaction commands plus an oracle). Agents carry out the interactions; a separate verification stage then checks the oracle against the recorded interaction trace by extracting data from it. All tools in the comparison use GPT-4o. On 30 interaction tasks in 8 apps (10 per difficulty level, levels by ideal step count and vagueness), task completion was 1.00, 0.80 and 0.50 by level, 0.77 on average, against 0.50 for MobileAgent and 0.40 for AppAgent; the share of correct steps was 0.94 against 0.60 and 0.49. For verification, 20 oracles were paired with a correct and an anomalous trace (40 tasks): oracle accuracy was 0.95 on correct and 0.85 on anomalous traces, against 0.90 and 0.30 for a two-turn GPT-4o prompt; 18 of 20 injected anomalies were found with 2 false positives (recall 90%, false-positive rate 4.5%). At Meituan it ran 10 requirements with 18 verification points over 10 weekly regression rounds in two months, found 4 new bugs and saved 1.5 person-days per round. The authors list as limitations that interaction and verification are separate, that general-purpose models lack domain knowledge (they plan retrieval-augmented generation) and that multimodal models hallucinate, especially in OCR.
- **What it means for AYNA:**
  - It is the closest prior work to C1: a natural-language requirement turned into a GUI test. Even with GPT-4o, half of the tasks at the hardest level failed, so RQ3's 60% step-level target for a local 7–8B model in Turkish is not a formality. RQ3 should report results per difficulty level, as they do.
  - Their metrics fit RQ3 (#77): "correct steps" is close to our step-level accuracy, and task completion is close to "the scenario needs no manual fix" (the end-of-project criterion).
  - Doing and verifying are separate, as in AYNA's step schema, where `Verify` steps are explicit checkpoints. The difference is that AYNA's checkpoints are written and approved while authoring and checked deterministically during playback. A model as run-time oracle, even their best one, gave false alarms, and a plain prompt caught only 30% of anomalies: both false fails and false passes (RQ5).
  - Their planned future work, retrieval of domain knowledge, is what the repository provides to C1 (#57).
  - Gap: mobile, cloud model, a small custom benchmark (30 tasks, 20 oracles), and a preprint.
- **Source checked:** full text of arXiv v1 (HTML), sections 3–5 and Tables 4–5 (2026-10-27). The text contradicts its own tables in places (e.g. 32 vs 64 verification points; the baseline's anomaly accuracy is 0.30 in Table 5 but 0.35 in the text; unfilled "xx" placeholders in the introduction), so the numbers above follow the tables.

#### [40] Zhang et al. — UFO: a UI-focused agent for Windows OS interaction

- **Citation:** C. Zhang, L. Li, S. He, X. Zhang, B. Qiao, S. Qin, M. Ma, Y. Kang, Q. Lin, S. Rajmohan, D. Zhang, Q. Zhang, "UFO: A UI-focused agent for Windows OS interaction," Proc. NAACL 2025 (Volume 1: Long Papers), pp. 597–622, 2025. DOI 10.18653/v1/2025.naacl-long.26. arXiv:2402.07939.
- **Finding:** UFO completes user requests in Windows applications with two GPT-4V agents. A HostAgent chooses the application from a desktop screenshot and the list of open windows; an AppAgent chooses a control and an action from three screenshots (the previous one with the last control highlighted, a clean one, and one with numbered control labels) plus the names and types of the available controls. Controls are found and operated through pywinauto with the UI Automation backend (10 control types; Click, SetText, GetText, Scroll, plus two custom actions). A safeguard asks the user before sensitive actions such as sending, deleting or closing. On 50 requests in 9 applications (Outlook, Photos, PowerPoint, Word, Adobe Acrobat, File Explorer, VS Code, WeChat, Edge; 5 per application plus 5 across applications), UFO succeeded on 86%, with an 89.6% completion rate and 5.48 steps on average; text-only GPT-4 and GPT-3.5, whose suggested steps a person carried out, succeeded on 42% and 24%. Success ranged from 60% (Acrobat) to 100% per application. Because GPT-V "may generate different outputs each time", each request was run three times and the best run reported; no variance is given. Latency and cost are not reported. The authors trace Acrobat's poor result to controls that UI Automation does not expose and plan a Win32 backend and GUI-specific vision models.
- **What it means for AYNA:**
  - It runs on AYNA's technical base (pywinauto `uia`, brief item 1) and shows that control names and types from UIA are enough for a model to choose the right control in real Windows apps. Giving the NL model repository objects with their `ControlType` (C1) is a smaller, offline version of the same input.
  - Its main failure is AYNA's RQ1 risk: controls that UIA does not expose. Its authors' remedy, a Win32 backend, is our win32 fallback (#23); D3 (#65) covers the visual side.
  - It is the reason behind the ADR: the model chooses every action during execution, outputs differ between runs, and the paper reports the best of three. A regression test that may take another path on an unchanged build is flaky by construction (RQ2). AYNA keeps the model but moves it to authoring (section 2.4).
  - Its safeguard (ask before a risky action) is the same "propose, a person approves" pattern as AYNA's healing gate (decision 2026-10-20).
  - Gap: a task-completion agent, not a testing tool (no oracle or verdict); cloud model; English; no object repository; 86% is a best-of-three result on 50 requests.
- **Source checked:** full text of arXiv v5 (HTML, May 2024): method, evaluation and limitations; venue and pages from the ACL Anthology entry (2026-10-27). The NAACL camera-ready was not compared with v5.

### 2.2 Grounding and output control

#### [41] Lewis et al. — Retrieval-augmented generation (RAG)

- **Citation:** P. Lewis, E. Perez, A. Piktus, F. Petroni, V. Karpukhin, N. Goyal, H. Küttler, M. Lewis, W. Yih, T. Rocktäschel, S. Riedel, D. Kiela, "Retrieval-augmented generation for knowledge-intensive NLP tasks," NeurIPS, 2020. arXiv:2005.11401.
- **Finding:** RAG combines a generator (BART-large, about 400M parameters) with a non-parametric memory: a dense retriever (DPR, two BERT-base encoders) over 21M 100-word chunks of Wikipedia in a FAISS index. The top-k retrieved passages condition the generator, either one passage for the whole answer (RAG-Sequence) or a mix per token (RAG-Token). Only the query encoder and the generator are fine-tuned; the document index stays fixed. In open-domain question answering (exact match) it beat the best baselines on Natural Questions (44.5 vs 41.5), WebQuestions (45.5 vs 41.1) and CuratedTrec (52.2 vs 50.6), but not on the standard TriviaQA split (56.8 vs 57.9). In Jeopardy question generation, human raters judged RAG more factual than BART in 42.7% of 452 pairs and BART more factual in 7.1%. Swapping the 2016 Wikipedia index for the 2018 one without retraining kept answers about world leaders current: 70% and 68% correct with matching index and question year, 12% and 4% with mismatched ones. The model also answered 11.8% of Natural Questions correctly when no retrieved passage contained the answer, i.e. from its own parameters.
- **What it means for AYNA:**
  - C1 follows this design: the object repository is the non-parametric memory. The objects of the current screen and the nearest repository objects (graph + vector retrieval, #57) go into the prompt, so the model never has to "know" the application.
  - The index swap is what happens when the UI changes: the repository is updated (or healed, C2) and the assistant follows without retraining. No model is trained on the customer's application, which also suits the closed network.
  - H2 (the same model with and without repository context) is AYNA's version of their "with vs without retrieval" comparison; #77 should keep the generator fixed and vary only the context.
  - The 11.8% shows that a generator does not stay inside what it retrieved. That is useful for trivia and harmful for a step target, so a target outside the repository is rejected by the validator (decision 2026-10-20) or made impossible by the grammar ([42], [43]).
  - Gap: English Wikipedia question answering with a trained retriever; AYNA uses an off-the-shelf embedding model, a small structured corpus and no fine-tuning.
- **Source checked:** abstract page and full text (ar5iv HTML of arXiv v4): sections 2–4, Tables 1 and 4, and the index hot-swap experiment (2026-10-27).

#### [42] Willard, Louf — Efficient guided generation for large language models

- **Citation:** B. T. Willard, R. Louf, "Efficient guided generation for large language models," arXiv:2307.09702, 2023 (preprint; implemented in the open-source Outlines library).
- **Finding:** The paper recasts constrained generation as moving through a finite-state machine built from a regular expression. Before generation, an index maps every state of the machine to the vocabulary tokens that keep the text valid; at each step the logits of all other tokens are masked, so the cost per token is O(1) on average instead of a scan over the vocabulary. Context-free grammars are handled the same way with an LALR(1) parser (a pushdown automaton); the index for a slightly extended Python grammar was about 50 MB. Against the Guidance library, which re-matches from the start of the text at every step, the authors describe the scaling difference as "striking" but qualify it. The guarantee is structural only: the output always matches the regex or grammar; the paper makes no claim about whether its content is right.
- **What it means for AYNA:**
  - This is the mechanism behind "grammar-constrained JSON" in the plan (Ollama's `format`, llama.cpp's grammars [43]): the model cannot produce a step that breaks the schema's syntax.
  - If the generation grammar lists the allowed values (keyword as an enum, `target` as an enum of the retrieved repository objects), an out-of-repository target becomes impossible to generate, not just rejected afterwards. Building that grammar per request is cheap, so #37 can try it.
  - A forced choice has the same weakness as Similo's "always returns something" [7]: if the right object was not retrieved, the model must still pick a listed one. The grammar should allow an explicit "no matching object" value, and retrieval recall must be measured.
  - Structure is not meaning. Our spike (#7) shows both limits: a free string let gemma4 run for 3,712 tokens without closing the JSON (finding 1: add `maxLength` and a token cap), and qwen3 produced schema-valid JSON that silently dropped a step (finding 2). A person still approves every generated step.
  - Gap: a preprint that measures speed only, not output quality.
- **Source checked:** abstract page and full text of arXiv v4 (HTML): method, the comparison with Guidance and the context-free grammar extension (2026-10-27). The timing plot's values could not be read from the HTML text.

#### [43] llama.cpp — GBNF grammars and JSON Schema constraints

- **Citation:** ggml-org, "GBNF Guide," `grammars/README.md` in the llama.cpp repository, https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md (accessed 2026-10-27). Project documentation, not a paper.
- **Finding:** GBNF (GGML BNF) defines formal grammars that constrain llama.cpp's output, for example to valid JSON. A grammar is passed with `--grammar` / `--grammar-file` on the command line or in the `grammar` field of a llama-server request. A JSON Schema can be given instead (`--json` / `-j`, the `json_schema` field, or `response_format` on `/chat/completions`) and is converted to a grammar. The schema "is only used to constrain the model output and is not injected into the prompt", so the prompt must describe the structure itself. Only a subset of JSON Schema works: unsupported features "are skipped silently"; `additionalProperties` defaults to false; `properties` mixed with `anyOf`/`oneOf` is not supported; `minimum`/`maximum` apply only to integers; nested `$ref`s are broken and remote ones unsupported; `pattern` must be anchored with `^…$`; `uri` and `email` formats, `patternProperties`, `uniqueItems`, `not` and conditionals are missing. Grammars "have performance gotchas": a long chain of optional items can make sampling extremely slow, so `x{0,N}` should be used.
- **What it means for AYNA:**
  - The step schema (`schemas/step.schema.json`, #13) is a frozen shared contract. The AI service needs a generation schema derived from it that stays inside this subset, and must check the converted grammar, because a dropped keyword is a constraint we think we have but do not. Full JSON Schema validation and the repository validator still run after generation.
  - The prompt must still describe the step format and list the objects; the schema constrains but does not inform. The #7 spike did both (Ollama `format` plus an object list in the system prompt).
  - `maxLength` on strings becomes a bounded repetition, the fast form, so the fix for the #7 runaway costs little.
  - The spike used Ollama, not llama.cpp; whether Ollama's `format` has the same gaps was not checked here, so #37 should test the real schema in both runtimes before D4.
  - Gap: documentation without evaluation; it does not say how masking works ([42] does) or what happens when generation hits the token limit before the JSON closes.
- **Source checked:** the README on the `master` branch (2026-10-27).

### 2.3 Decision models and calibration

#### [44] Guo, Pleiss, Sun, Weinberger — On calibration of modern neural networks

- **Citation:** C. Guo, G. Pleiss, Y. Sun, K. Q. Weinberger, "On calibration of modern neural networks," ICML, 2017. arXiv:1706.04599.
- **Finding:** A model is calibrated when its confidence equals its accuracy: of the answers given with confidence 0.8, 80% are right. The paper measures this with reliability diagrams, the Expected Calibration Error (ECE: predictions in M = 15 equal-width confidence bins, weighted mean gap between accuracy and confidence) and the Maximum Calibration Error (largest gap). Modern networks are more accurate but worse calibrated: on CIFAR-100, LeNet-5 has 44.92% error and 4.85% ECE, ResNet-110 27.83% error and 16.53% ECE. Depth, width, batch normalisation and less weight decay make calibration worse. Temperature scaling divides the logits by a single scalar T fitted on a held-out validation set; it does not change which answer is chosen, so accuracy stays the same. It cut ECE for ResNet-110 on CIFAR-100 from 16.53% to 1.26% and for ResNet-152 on ImageNet from 5.48% to 1.86%, and was the best or close to the best of the methods compared (histogram binning, isotonic regression, Bayesian binning, vector and matrix scaling), as well as the fastest. On Reuters it did not help (0.85% → 0.91%). The study covers image and document classifiers, not language models.
- **What it means for AYNA:**
  - The semester-2 decision layer acts on a model's confidence: below the threshold the decision goes to a person (decision 2026-10-20 decision layer in semester 2). That only works if the confidence is calibrated on *our* decisions; the labelled decision log from semester 1 (#63) is the held-out set on which to draw reliability diagrams, compute ECE and fit T. No vendor's calibration figure transfers ([45]–[47]).
  - The same holds for C2's healing score. A similarity of 0.8 is not a probability; before a threshold on it is read as "80% sure" (minimum score for a proposal, or semester-2 decisions), check its reliability on the RQ4 data (#76) and calibrate if needed.
  - D7's criterion, the share of decisions taken at 5% error, is a coverage-at-risk measure that is only meaningful with calibrated scores.
  - Report ECE with 15 equal-width bins and a reliability diagram, so our numbers are comparable with this paper and with the model cards that use the same binning [47].
  - Gap: 2017 classifiers; with a small panel, many bins hold few examples, so report the bin counts.
- **Source checked:** abstract page and full text (ar5iv HTML): sections 2–5, Table 1 and supplementary Table S2 (2026-10-27).

#### [45] TypeSafe — Jev, a "System One" decision model

- **Citation:** D. Almeida, "Introducing System One models and Jev," TypeSafe blog, 2026, https://typesafe.ai/blog/introducing-system-one-models-and-jev (accessed 2026-10-27). Vendor blog post.
- **Finding:** The post introduces "System One models", made to take fast, structured decisions that software can use directly, as opposed to chat models: "unstructured state in, typed probabilistic decisions out". The possible outputs are defined in advance, every answer comes with calibrated probabilities and a confidence, and a question can have up to 255 options (more through two stages). The model is trained with "Reinforcement Learning for Calibrated Decisions" (RLCD), which the post does not explain. It claims 70–500 ms end-to-end against 3–329 s for frontier models and states that type errors are impossible by construction; its "0% hallucination" figure is labelled as not empirical. No calibration measurement (ECE, reliability diagram), model size or weights are given. Jev is offered in early access through TypeSafe's hosted API; a wrapper repository lets other language models produce decisions in the same format. The page shows two dates (byline 15 September 2026, metadata 19 October 2026).
- **What it means for AYNA:**
  - It defines the interface the plan calls "Jev-compatible": a question with typed options in, a probability per option out. AYNA's three decision points fit it: which candidate is the missing element (choice), is this window expected (yes/no), how serious is this failure (score).
  - Jev itself cannot be used: it is a hosted API, and AYNA calls no external service (brief, "Problem"; `/AGENTS.md` §9). Only the interface is reusable; the model has to be an open-weight one that runs locally ([46], [47]).
  - "Calibrated" is asserted, not shown; on our data it has to be measured ([44]).
  - Gap: marketing material without reproducible numbers.
- **Source checked:** the blog post (2026-10-27). The FAQ answers, the documentation of output types and the evals site (evals.typesafe.ai) were not read.

#### [46] Strands Labs — Strands Decider

- **Citation:** Strands Labs, *Strands Decider*, GitHub repository README, https://github.com/strands-labs/strands-decider (Apache-2.0; accessed 2026-10-27).
- **Finding:** "A small, fast decision model, or system one model, for agentic workflows" — it does not generate text. It answers three question types: `choice` (one of N options), `noul` (yes/no, as the probability of yes) and `score` (a level on an ordered rubric), with per-option probabilities and a confidence. It runs from a CLI or a local HTTP server (`/v1/systemone`) on CPU, CUDA GPUs or Apple silicon. The reference model `strands-decider-2B-qwen3.5-v1-2610` has 1.9B parameters (Qwen3.5 base); Gemma-4-based variants range from E2B to 26B-A4B. On JevBench (231 tasks) the v1 model scores 180/231 (0.779) with Brier score 0.280 and ECE 0.072; the Gemma 4 variants score 180–207/231. Median latency is 115 ms on an RTX 3090 and 153 ms on an M3 Pro. The README claims that on unseen short classification tasks, answers with confidence 0.9 or more are right about 95% of the time, and advises asking a person below 0.9; there is no built-in abstention. The author warns that 231 tasks are few and that differences under about 10 tasks between single runs are unresolved. Turkish is not mentioned.
- **What it means for AYNA:**
  - A concrete local, Apache-2.0 candidate for D7, small enough for team laptops, and its three question types match AYNA's three decision points (see [45]).
  - Its own advice, "below 0.9, ask a person", is AYNA's semester-2 policy. Our threshold must come from our panel, not from theirs.
  - Its numbers move between sources (llmreference.com lists 176/231 for a later version, which the README itself shows as a separate single run), and the author calls small gaps noise. Leaderboard positions cannot decide D7; our Turkish panel does (plan, D7).
  - Gap: vendor-reported, English-centric, evaluated on short classification tasks, not on GUI-testing decisions.
- **Source checked:** the README (2026-10-27). The linked `evaluation/results.md` was not read.

#### [47] H2O.ai — H2O-Lightning-4B

- **Citation:** H2O.ai, "H2O-Lightning-4B ranks first on JevBench open-weights leaderboard," press release (Business Wire), 12 October 2026, read as reprinted by FinancialContent; model card https://huggingface.co/h2oai/h2o-lightning-4b (v1.4.1, accessed 2026-10-27). The plan links the BigDATAwire (HPCwire) reprint of the same release.
- **Finding:** An Apache-2.0 fine-tune of Qwen3.5-4B (the card lists 5B parameters and 9.3 GB of weights) for typed decision questions about a record (a document, ticket, policy or conversation, plus up to 4 images). It has the same three question types as [46] and returns a probability for every option, in one forward pass and one output token; it is "not a chat model" and gives no explanations. It runs on vLLM (a fork for the recommended mode), Transformers, or a GGUF build for llama.cpp; latency is reported only on GPUs (about 28 ms per question on an L40S for short records), and CPU inference is not discussed. By default, yes/no answers are reported with at least 0.801 on the chosen side, so no shipped yes/no answer falls between 0.2 and 0.8; the card says to turn this floor off (`SHIM_NOUL_FLOOR=0`) when uncertain answers are escalated to a person. The release reports JevBench v1.6.1 (as of 7 October) with a composite score of 72.5 (calibration 90, speed 92.6, intelligence 60, cost 60), first of 104 open-weight systems and ahead of Jev at 71.5, while noting that about one point separates the top of the board. The card reports 206/231 on the public JevBench items (89.2%) and a calibration error of 0.0705 (top-option probability, 15 equal-width bins) on its own Decision Index; it was "evaluated mostly in English". All numbers are self-reported.
- **What it means for AYNA:**
  - It is the plan's D7 default, and its open weights, licence and GGUF build fit the closed network and the llama.cpp route.
  - Two things to check before relying on it: CPU speed on team hardware is unpublished (the plan's "runs on CPU" is not shown for this model), and Turkish was not evaluated.
  - The yes/no floor matters for AYNA: with it on, a confidence threshold between 0.2 and 0.8 never fires. Any threshold experiment in #103 must run with the floor off.
  - A one-point lead on a composite of intelligence, calibration, speed and cost says little about our decisions; D7 compares it with Decider and others on our panel, as the plan already says.
  - Gap: vendor-reported, mostly English, no GUI-testing evaluation.
- **Source checked:** the Hugging Face model card (v1.4.1) and the Business Wire release on FinancialContent (2026-10-27). The plan's HPCwire link returned 403. The JevBench repository and leaderboard were not read; the llmreference.com listing of the 231 public items was (vendor-reported values only).

### 2.4 Why AYNA uses the language model only at authoring time

AYNA's model writes steps; it never runs them (decision 2026-10-20 language models only at authoring time). The sources give four reasons. *Repeatability:* the systems that let a model choose actions during execution report the best of three runs because outputs differ between runs (GPTDroid [15], UFO [40]); a regression test that may take another path on an unchanged build is flaky by construction (RQ2). *Verdicts:* a model that judges results at run time raises false alarms and misses bugs (AUITestAgent's verifier had a 4.5% false-positive rate; a plain GPT-4o prompt judged only 30% of anomalous traces correctly [16]), and a run that passes because the model improvised is exactly the false pass RQ5 counts. *Validity:* constrained decoding guarantees syntax, not meaning [42][43], and our own spike produced a schema-valid answer that dropped a step (#7), so a person must review each generated step, and a person is present only while a test is being written. *Closed network and cost:* a local 7–8B model needed a median of about 3–6 s per sentence on a team laptop (#7); that is fine once per authored step but not at every step of every CI run, and authoring is where repository context is available to ground the model [41]. So the model's suggestions are checked against the repository, approved by a person and frozen as JSON steps, and playback replays them deterministically, also when the AI service is down. The semester-2 decision layer keeps this shape: a rule first, a local decision model only when no rule applies, a person below the confidence threshold [44], and every approved decision becomes a rule.
