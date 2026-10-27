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
| LLMs in testing | Survey [14]; GPTDroid [15]; AUITestAgent [16] | AUITestAgent reached a 77% task completion rate from natural-language requirements on mobile apps | Mostly mobile/web and cloud models; not desktop, not closed-network, not tied to an object repository |
| Commercial tools | TestComplete [21], Ranorex [32], UFT One [31] | Recorder, object repository, keyword tests, reports | Per-user licences; TestComplete's basic plan starts at about $1,210 per user per year [22] |
| Open-source tools | FlaUI [18], pywinauto [33], WinAppDriver [19], Robot Framework [20] | Programmatic UI Automation access; keyword-driven testing | No recorder, repository or self-healing; WinAppDriver's latest stable release is v1.2.1 and it has not had a new stable release for years |

## Section 2 — Language models in GUI testing, decision models (#20)

*To be written under #20 (galip).*
