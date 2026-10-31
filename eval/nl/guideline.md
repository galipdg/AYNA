# Turkish NL dataset — writing and labelling guideline

| | |
|---|---|
| Issue | #36: this guideline and the first 40 pairs, written together with Hasan |
| Next | #57: grow to 100 pairs (at least 20 by outsiders) and freeze a 30-pair held-out split |
| Used by | #37 (constrained generation: 100 % of outputs on the 40 pairs parse and validate), #71 (model comparison), #77 (RQ3: step-level accuracy with and without repository context) |
| Contract | Gold steps are `schemas/step.schema.json` v0.1 documents (#13, ADR `2026-10-27-step-schema-v0`) |
| Files | `pairs.jsonl` (dev set) · `heldout.jsonl` + `heldout.sha256` (frozen split, from #57) · `objects/<app>.json` · `pair.schema.json` · `objects.schema.json` · `check_pairs.py` |

A **pair** is one Turkish test description, written as a tester would write it, together with its **gold steps**: the step document a perfect NL assistant would return for it. This file says how to write the description, how to label the gold steps and how pairs are stored, reviewed and used. Section numbers are referenced from the pairs' `notes` and from `check_pairs.py`.

## 1. Purpose and how the set is used

- **What it measures.** The NL assistant (C1) turns a description plus the app's repository objects into steps. #77 compares its steps with the gold steps, with and without repository context, on the held-out split. #37 and #71 run on the dev set.
- **Dev set and held-out split.** `pairs.jsonl` is the dev set: anyone may read it, debug on it, take few-shot examples from it and tune prompts on it. In #57, before any prompt tuning, 30 sample-app pairs are **moved** from `pairs.jsonl` into `heldout.jsonl` in one commit that also adds `heldout.sha256` (`shasum -a 256 heldout.jsonl > heldout.sha256`). The split is made **by scenario**: all variants of one scenario (§2) go to the same side, so no paraphrase of a held-out pair is ever seen in tuning. Stratify by scenario type and origin (team/outsider).
- **Never tune on the held-out split.** Do not read its texts while writing prompts, few-shot examples, object descriptions or retrieval code; do not run it to "see how we are doing". It is run once per condition for the RQ3 report (#77). `ai/AGENTS.md` says the same.
- **A frozen split is never edited.** `check_pairs.py` fails if `heldout.jsonl` no longer matches `heldout.sha256`. A labelling error found after the freeze is reported in the RQ3 report, not fixed. Before tuning has started, a documented re-freeze (new hash, reason in the #57 task note) is allowed once.
- **What counts.** The 40 pairs of #36 and the 100 of #57 count only `app: "sample"` pairs (sample app v1.0, #33). The `trial` pairs in `pairs.jsonl` are worked examples on the one-screen trial app (#9): they prove the format end to end, stay in the dev set and can serve as few-shot examples, since they are on another app.
- **How a result is compared (input for #77).** A generated step equals a gold step when `keyword`, `target`, `value`, `checkpoint` (`property`, `operator`, `expected`) and `timeoutMs` are all equal. Gold steps carry no `id`. How generated and gold steps are aligned for step-level accuracy is #77's decision; the labelling rules below make the gold deterministic so that exact comparison is fair.

## 2. Record format

One JSON object per line, UTF-8, Turkish characters written as they are (not `\u` escapes). `pair.schema.json` is the formal definition; the checker validates every line against it.

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | `<app>-NNN`, e.g. `sample-007`. Unique across `pairs.jsonl` and `heldout.jsonl`, never reused. |
| `app` | yes | App code: `sample`, `trial`. `objects/<app>.json` must exist. |
| `appVersion` | yes | Version the pair was written for; equals `appVersion` in `objects/<app>.json` (sample: the title-bar version, `1.0`; trial: the commit of `app.py`, since it shows none). |
| `scenarioType` | yes | One of the eight types in §3. |
| `scenario` | yes | Id of the test intent, e.g. `sample-login-ok`. Pairs with the same scenario are **phrasing variants**: same app, version, type and identical gold steps. A text that needs different gold is a different scenario. |
| `style` | yes | Phrasing style (§5): `imperative`, `polite`, `descriptive`, `terse`, `stepwise`. |
| `tags` | no | Difficulty markers (§5): `implicitTarget`, `informal`, `reordered`. |
| `origin` | yes | `team` or `outsider` (#57). |
| `author` | yes | `galip`, `hasan`, `omer`; for outsiders an anonymous code `ext-01`, `ext-02`… — never a name. |
| `text` | yes | The description exactly as written. Line breaks are allowed (numbered lists); no leading or trailing white space. |
| `gold` | yes | Step document `{"version": "0.1", "steps": [...]}` with at least one step and no step `id`. |
| `notes` | no | Labelling choices a reviewer should know, with the rule number. |

A worked example (pretty-printed here; in the file it is one line):

```json
{
  "id": "trial-002", "app": "trial", "appVersion": "5e23d15",
  "scenarioType": "login", "scenario": "trial-login-ok", "style": "polite",
  "origin": "team", "author": "galip",
  "text": "Lütfen kullanıcı adına ve şifreye admin yazıp Login'e tıklayın; ardından durum mesajının \"Welcome, admin!\" olduğunu kontrol edin.",
  "gold": {"version": "0.1", "steps": [
    {"keyword": "Type", "target": "login.usernameInput", "value": "admin"},
    {"keyword": "Type", "target": "login.passwordInput", "value": "admin"},
    {"keyword": "Click", "target": "login.loginButton"},
    {"keyword": "Verify", "target": "login.statusLabel",
     "checkpoint": {"property": "name", "operator": "equals", "expected": "Welcome, admin!"}}
  ]},
  "notes": "One value for two coordinated fields gives two Type steps (6.2)."
}
```

**Object list** (`objects/<app>.json`, defined by `objects.schema.json`): the repository objects of one app version that gold steps may target — `app`, `appVersion`, `source`, and `objects`, a map from logical name to `automationId` (exactly as UI Automation reports it), `controlType` (UIA control type name), a short Turkish `description` (with the visible English text in parentheses if the UI is English) and, for combo boxes and lists, `items` (the item texts exactly as shown). It is copied from the real app (UIA dump, source, the app's own UIA tests), **never invented**. Logical names follow `screen.element` in lowerCamelCase (`conventions.md`). The descriptions are what the NL assistant sees about each object (`{name: description}` is the generator's `--objects` input), so describe the control neutrally, as a tester would name it, and do not copy phrases from pair texts into it.

## 3. Scenario types

The types follow the sample app's screens (#33) and the reference scenarios in `docs/rs/scenarios.md` (#34), plus two types defined by the kind of step. Assign the **first** that applies:

1. only Verify steps → `checkpoint`;
2. at least one Wait step → `wait`;
3. otherwise the type of the screen most steps act on (on a tie, the first such screen).

`check_pairs.py` enforces rules 1 and 2 in both directions.

| Type | What the pair does | Sample-app screen | Reference scenarios |
|---|---|---|---|
| `login` | Types credentials, logs in, checks the welcome or error text | Login | SC-14, SC-17, SC-21, SC-26 |
| `form` | Fills fields, chooses from a combo box, saves or goes back, checks the result or a validation message | Detail form | SC-19, SC-22, SC-34 |
| `listSearch` | Searches, picks an item from a list, opens it | List screen | SC-18 |
| `settings` | Switches tabs, toggles check boxes (§6.8), checks their state | Settings with tabs | SC-16 |
| `dialog` | Checks a modal dialog's message and answers it (Yes/No/OK) | Dialog | SC-20, SC-22 |
| `wizard` | Moves through pages with Next/Back/Finish, selects on a page, checks the summary | Wizard | SC-20 |
| `checkpoint` | Only checks: texts and states, no action | any | SC-16, SC-21 |
| `wait` | Waits explicitly for a control, with or without a time limit | any (the list screen's late grid) | SC-18, SC-19 |

**Reading results per type.** Six types name a screen, but `checkpoint` and `wait` name a kind of step, and rules 1 and 2 come first. A login scenario with one explicit wait is therefore a `wait` pair, and the `wait` type mixes every screen. Accuracy per scenario type is not accuracy per screen: say so wherever per-type results are reported (#77, the thesis).

**Quotas.** #36 (40 sample-app pairs): 5 pairs per type, from at least 2 scenarios, in at least 3 styles (the acceptance criterion "≥ 3 phrasing variants per scenario type" is read as ≥ 3 distinct `style` values per type, which the checker counts). Across the 40, use every style at least 4 times and tag about a quarter `implicitTarget`. #57 (100): 12–13 per type; outsider pairs fill whichever types they fall into.

**Grids.** Schema v0 cannot select or check a grid row (`Verify main.customerGrid name contains "Yılmaz"` checks the grid's UIA Name, not its rows; #37). A `listSearch` pair may Select only in a list or combo box; a grid row is out of scope (§6.7) until a later schema version.

## 4. Turkish vocabulary

The NL assistant must understand many surface forms; the gold is the same for all of them. These tables say which step a phrase maps to. Examples use the sample app's planned names from #34; they become real once `objects/sample.json` exists.

### 4.1 Actions

| Turkish (typical forms) | Keyword | Example → gold step |
|---|---|---|
| tıkla, bas (tıklayın, basıp, bastıktan sonra, basınca) | Click | *Kaydet'e tıkla* → Click `detail.saveButton` |
| işaretle, tikle (an unchecked check box); işaretini kaldır (a checked one) | Click | *Remember me kutusunu işaretle* → Click `login.rememberMeCheckBox` (it starts unchecked). Click toggles: only the form that changes the box from its start state is a pair, and `notes` names that state (§6.8) |
| aç, geç, seç (a tab, a radio button, a menu item) | Click | *Bildirimler sekmesine geç* → Click `settings.notificationsTab` |
| yaz, gir, doldur, … olarak gir / ayarla / değiştir, … yap (edit box) | Type | *Ad alanını Ayşe ile doldur* → Type `detail.nameInput` "Ayşe" |
| temizle, sil, boşalt (edit box) | Type with `""` | *Arama kutusunu temizle* → Type `main.searchInput` "" |
| seç, … olarak seç, … yap (combo box, list) | Select | *Departman olarak Kalite Güvence'yi seç* → Select `wizard.departmentCombo` "Kalite Güvence" |
| doğrula, kontrol et, emin ol, bak, … olmalı, … görünmeli, … yazmalı, … beklenir | Verify | §4.2 |
| bekle, … görünene / gelene / açılana / etkinleşene kadar bekle | Wait | §4.3 |

**Implicit actions.** Some verbs name a goal, not a control. Expand them into the steps a tester performs on that screen (§6.2): *giriş yap* (Click the login button, after any credentials the text gives), *admin/admin ile giriş yap* (Type user name, Type password, Click login), *Yılmaz'ı ara* (Type the search box, Click the search button), *kaydet* (Click Save), *onayla* (Click Yes/OK), *vazgeç / iptal et* (Click No/Cancel), *ileri / geri git* (Click Next/Back), *bitir* (Click Finish), *kapat* (Click the dialog's close or OK button), *kaydı sil* (Click the screen's delete button; *sil* is Type `""` only on an edit box).

### 4.2 Checks

**Property** — decided by what is checked and the target's control type (§6.3):

| The text checks … | `property` and `expected` | Control types |
|---|---|---|
| the text a label, message, button, tab or window title shows | `name`, the text | any |
| the text inside an edit box or combo box | `value`, the text | Edit, ComboBox, Document |
| aktif, etkin, tıklanabilir, kullanılabilir / pasif, devre dışı, etkin değil, gri | `enabled`, true / false | any |
| görünür, görünüyor, ekranda, çıkıyor / görünmüyor, gizli, ekranda yok | `visible`, true / false | any |
| işaretli, seçili, tikli / işaretsiz, işaretli değil (check box) | `checked`, true / false | CheckBox |
| seçili / seçili değil (radio button, list item, tab) | `selected`, true / false | RadioButton, ListItem, TabItem, DataItem |
| boş (a label) / boş (an edit box) | `name` equals `""` / `value` equals `""` | Text… / Edit, ComboBox |

**Operator** for text properties:

| Phrase | `operator` |
|---|---|
| X olmalı, X yazmalı, X yazıyor, X olduğunu, X yazdığını, X göstermeli, tam olarak X, X mesajı / hatası görünmeli / çıkmalı, durum = X | `equals` |
| X içermeli, X içerdiğini, X geçmeli, X geçtiğini, içinde X geçmeli | `contains` |
| X olmamalı, X yazmamalı, X'ten farklı olmalı | `notEquals` |

- **Booleans take only `equals`.** Negation goes into `expected`: *işaretli olmamalı* → `checked` equals `false`; *aktif değil* → `enabled` equals `false`.
- **A literal wins over visibility.** *'Kayıt başarılı' mesajı görünmeli* → `name` equals "Kayıt başarılı" on the message label, not `visible`. With no literal (*hata mesajı görünmeli*) → `visible` equals `true` on the error label.
- **Two conditions are two steps.** *Kaydet aktif ve görünür olmalı* → Verify `enabled`, then Verify `visible`, in text order.
- Not expressible in v0 (§6.7): starts/ends with, does not contain, numeric comparison, counts, grid rows.

### 4.3 Waits and time limits

- *X görünene / gelene / açılana / yüklenene / etkinleşene / aktif olana kadar bekle* → Wait X. Wait means "until the target exists, is visible and enabled".
- A time limit sets `timeoutMs` on **the step it modifies**: *en fazla 10 saniye*, *en çok 10 sn*, *10 saniye içinde*, *max 10 sn*, *10 saniyeden kısa sürede* → 10000; *1 dakika* → 60000; numbers in words (*beş saniye*) the same. *Login'e tıkla, durum etiketinde 5 saniye içinde 'Welcome, admin!' yazmalı* → the Verify gets 5000.
- No limit in the text → no `timeoutMs` (the run's default applies).
- A temporal clause without *bekle* (*sonuçlar gelince Aç'a tıkla*, *pencere açıldıktan sonra …*) adds **no** Wait: every step already waits for its own target.
- Out of scope: a fixed sleep (*3 saniye bekle* with no target) and waiting until something disappears (*kaybolana kadar bekle*).

### 4.4 Suffixes, quotes and apostrophes

- Values may be quoted (`'…'`, `"…"`, `“…”`, `‘…’`) or bare. Quotes are never part of the value.
- A case suffix after an apostrophe or a closing quote is dropped: *Ankara'yı* → "Ankara"; *"Kalite Güvence"yi* → "Kalite Güvence"; *'Welcome, admin!' yazdığını* → "Welcome, admin!"; *1234'ü* → "1234".
- **Team pairs: quote a value whose end could read as a suffix.** Some values end in what looks like a case or possessive suffix (*Kalite Güvencesi*, *admini*). Written bare, *Kalite Güvencesi* reads as "Kalite Güvencesi" or as "Kalite Güvence" + *-si*. The checker cannot tell either: both strings are in the text. Team writers quote such a value (*'Kalite Güvencesi' seç*). The reviewer checks this (§9).
- **Team pairs: never glue a suffix to a bare value.** In a team text a bare value stands as a whole word, with nothing attached: write *Ankara'yı*, not *Ankarayı*. `check_pairs.py` enforces this for `origin: team` (`bare-suffix`: the value occurs only with letters or digits attached).
- **Outsider texts are kept as written.** There a suffix written without an apostrophe (*Ankarayı*) is dropped the same way as after one. When a value could itself end in a suffix (*admini*: "admin" or "admini"?), label the most likely reading and record it in `notes`, e.g. `value read as "admin" (4.4)`.
- Suffixes on control names (*kullanıcı adı alanına*, *Kaydet butonuna*, *Kaydet'e*, *Logine*, *şifreye*) only identify the target. *Kaydet'e tıkla* targets the button whose text is "Kaydet". The quoting rules apply to values and expected texts, not to control names.

### 4.5 Verb forms

All forms of a verb give the same step; they mostly decide the style (§5).

| Form | Example | Usual style |
|---|---|---|
| informal imperative | tıkla, yaz, seç | imperative |
| formal / plural imperative, request | tıklayın, yazınız, lütfen …, tıklar mısınız | polite |
| first person plural | tıklayalım, yazalım | polite |
| passive, impersonal, conditional | tıklanır, girilir, basıldığında, girilirse | descriptive |
| necessity | tıklanmalı, girilmelidir, görünmelidir | descriptive |
| converbs | yazıp, yazarak, bastıktan sonra, basınca, basmadan önce | any |
| bare nouns, colons, arrows, `=` | *ad: Ayşe*, *Login*, *durum = 'X'* | terse |

A negated action (*Login'e tıklama*) is not a step; such texts are out of scope.

## 5. Phrasing variants

**Styles** (`style`, required, one per pair). The same scenario on the trial app in all five styles:

| Style | What it looks like | Example (`trial-login-ok` / `trial-login-wrong-password`) |
|---|---|---|
| `imperative` | Informal commands, clauses joined by commas, *ve*, converbs | *Kullanıcı adı alanına admin yaz, şifre alanına admin yaz, Login butonuna tıkla ve durum etiketinde 'Welcome, admin!' yazdığını doğrula.* |
| `polite` | Formal or plural imperative, requests, *lütfen* | *Lütfen kullanıcı adına ve şifreye admin yazıp Login'e tıklayın; ardından durum mesajının "Welcome, admin!" olduğunu kontrol edin.* |
| `descriptive` | Test-case prose: passive or impersonal voice, condition and expectation | *admin kullanıcısı yanlis123 şifresiyle giriş yapmaya çalıştığında 'Invalid username or password' hatası görünmelidir.* |
| `terse` | Notes: labels with colons or `=`, dropped verbs and suffixes | *kullanici adi: admin, sifre: admin, Logine tikla, durum 'Welcome, admin!' olmali* |
| `stepwise` | A numbered list or explicit sequence words (*önce, sonra, ardından, son olarak*) | *1) Kullanıcı adı alanına admin gir. 2) Şifre alanına yanlis123 gir. 3) Login butonuna bas. 4) Durum etiketinin 'Invalid username or password' olduğunu kontrol et.* |

**Tags** (`tags`, optional):

- `implicitTarget` — at least one target is not named, only implied by a goal (*giriş yap*, *admin/admin ile*, *kaydet*, *hatası görünmeli* with no label named).
- `informal` — written as people type in a hurry: no Turkish characters (*sifre*), no apostrophes (*Logine*), lower case, small typos. Values stay recognisable (§6.4); in a team pair a value still stands whole or quoted (§4.4).
- `reordered` — text order differs from execution order (*Login'e basmadan önce … yaz*).

**Writing useful variants.** Variants of a scenario must keep the meaning (identical gold) but differ in at least two of: verb form (§4.5); how controls are referred to (visible text *Login'e*, role noun *giriş butonuna*, goal only *giriş yap*); sentence structure (one compound sentence, several sentences, a list); connectors (*ve*, *-Ip*, *sonra*, *ardından*, *-DIktAn sonra*, *önce … sonra*); quoting; order. Do not make a variant by changing one word: the set should show how differently people write, not how robust a model is to synonyms alone. The checker rejects texts that are identical after folding case and diacritics.

## 6. Labelling gold steps

### 6.1 General

- **Only what the text asks.** No missing and no extra steps: no Click to focus an edit box before Type, no Wait before every step (each step waits for its target anyway, §4.3), no Verify the text does not ask for, no navigation the text does not mention.
- **One action per step**, in **execution order**, which is usually text order (*basmadan önce* reverses it, tag `reordered`).
- **Preconditions produce no step.** *Pencere ilk açıldığında …*, *Giriş ekranındayken …* describe the start state. A scenario starts on the screen of its first step's target, with the app in its default state there.
- **Ambiguity.** If two careful labellers could produce different gold, a team pair is rewritten until they cannot; an outsider pair gets the most likely reading and a `notes` entry, or is dropped (§8).

### 6.2 Implicit and coordinated actions

- A goal verb is expanded into the screen's real steps (§4.1): *admin/admin ile giriş yap* → Type `…usernameInput` "admin", Type `…passwordInput` "admin", Click `…loginButton` (user name first, then password, as the screen asks).
- One value for coordinated fields gives one step per field: *kullanıcı adına ve şifreye admin yaz* → two Type steps.
- One check on coordinated targets gives one Verify per target: *Kaydet ve İptal aktif olmalı* → two Verify steps.

### 6.3 Targets

- A target is a logical name from `objects/<app>.json` — the control the text means. If the text means a control that is not in the object list, the pair cannot be written (do not add objects that the app does not have).
- The keyword and checkpoint property must fit the control type (checked by `check_pairs.py`):

| Keyword or property | Allowed control types |
|---|---|
| Type | Edit, ComboBox, Document |
| Select | ComboBox, List (the value is one of the object's `items`) |
| Verify `value` | Edit, ComboBox, Document |
| Verify `checked` | CheckBox |
| Verify `selected` | RadioButton, ListItem, TabItem, DataItem |
| Click, Wait, Verify `name` / `enabled` / `visible` | any |

- A label's text is always `name`, never `value` (labels have no ValuePattern; #37 found models confuse the two). Do not check `value` on a password box: UI Automation hides it.

### 6.4 Values

- Type `value` is what is typed, verbatim from the text after §4.4: same case, same Turkish characters, inner spaces and punctuation kept.
- Select `value` is the item text exactly as the app shows it (`items` in the object list), even when the text writes it in lower case or without Turkish characters (*sehir: izmir* → "İzmir").
- Verify `expected` is the text exactly as written in the description (after §4.4). Every non-empty value and text `expected` must appear in the text; the checker compares ignoring case and diacritics, so an informal text still passes.
- **The gold follows the text, not the app.** A team pair of a positive scenario should also pass when played back on the app version: if it would not (wrong message, wrong item), fix the text. An outsider text is never edited: if it contradicts the app, label it literally and say so in `notes`.

### 6.5 Checkpoints

Apply §4.2: property from what is checked and the control type, operator from the phrase, booleans only with `equals` and negation in `expected`, an empty label is `name` equals `""`, an empty edit box `value` equals `""`. When the text gives no literal and no state word, there is no checkpoint to label: rewrite the text.

### 6.6 Waits and time limits

Apply §4.3: Wait only for an explicit *bekle* on a target; a time limit goes on the step the phrase modifies, converted to milliseconds; no limit, no `timeoutMs`.

### 6.7 Out of scope for step schema v0

Do not write texts that need any of these; drop outsider texts that contain them (and count them for #57, as a finding of what users ask for):

- double or right click, hover, drag and drop, scrolling;
- keyboard keys and shortcuts (*Enter'a bas*, *Tab*, *Ctrl+S*);
- appending to a field (*sonuna ekle*): Type replaces the text;
- setting a check box to the state it already has (*işaretini kaldır* on an unchecked box): Click toggles (§6.8);
- fixed sleeps and waiting until something disappears;
- grid or table rows and cells, item counts or order, numeric comparisons, starts/ends with, does not contain, patterns;
- conditions, loops, data-driven repetition (*eğer … ise*, *her şehir için*);
- starting or closing the app, other apps, file dialogs, screenshots or visual checks;
- negated actions as assertions (*Login'e tıklama*).

### 6.8 Check boxes

In playback (#40) a Click on a check box toggles it. Step schema v0 has no keyword for "make sure it is checked". If *işaretle* and *işaretini kaldır* both became the same Click, two texts with opposite meanings would share one gold, which teaches the model to ignore the negation. A pair would also become silently wrong on an app that starts in the other state (#145 review). So:

- **Start state.** The box's state where the scenario starts: the app's default on that screen (§6.1), unless an earlier step of the same pair changed it. Take it from the app (its source, README or a UIA check), never from the text. The trial app's *Remember me* box starts unchecked.
- **Only the form that changes the box.** On an unchecked box, *işaretle* / *tikle* → Click. On a checked box, *işaretini kaldır* → Click. The other form asks for the state the box already has. It has no correct gold in v0: do not write it (§6.7), and drop an outsider text that needs it (§8).
- **Record the state.** Every pair with a Click on a CheckBox says in `notes` which start state it assumed: `start state: unchecked` (or `checked`), naming the box when there are several. `check_pairs.py` requires the phrase (`start-state`); the reviewer checks that the state is right.
- A text that only checks a state (*işaretli olmalı*) is Verify `checked` (§4.2). It needs no start state.

A keyword that sets a state (`Check` / `Uncheck`, or Click with an expected end state) is a step-schema question for a version after v0.2 (#147).

## 7. Writing the sample-app pairs (once #33 lands)

The 40 pairs of #36 need the sample app's real controls and logical names. They are a fill-in job once sample app v1.0 (#33, which waits on D1 #21) exists:

1. **Object list.** Hasan runs the app's UIA dump (`uia_dump.py --json`, as for the trial app) and writes `objects/sample.json`: one entry per interactive control and per label a test may check, with the full AutomationId, control type, a Turkish description and `items` for every combo box and list; `appVersion` is the title-bar version. Galip reviews the logical names against the repository naming (`conventions.md`).
2. **Scenarios.** Two per type (§3), taken from the SC-xx scenarios in `docs/rs/scenarios.md` where they fit, with a short `scenario` id each (`sample-login-ok`, `sample-wizard-kalite`).
3. **Texts.** Five pairs per type in at least three styles (§5). Galip and Hasan each write about half, so the set is not one person's Turkish.
4. **Gold.** Label by §6; the other person reviews with the checklist (§9).
5. **Check.** `check_pairs.py` passes (§10). Ids continue `sample-001`, `sample-002`, … in the order pairs are added.
6. **Playback (when #26 exists).** Run the positive team scenarios on the app; a gold that fails on the app points to a wrong text or label.

## 8. Outsider pairs (#57)

At least 20 of the 100 pairs are written by people outside the team, so the set is not only our phrasing. Hasan collects them; galip and Hasan label them.

- **Who.** Turkish speakers who did not design AYNA: classmates, students of other departments, testers at HAVELSAN if possible. Aim for at least five people with 3–6 texts each, so that no single writer dominates.
- **Consent and privacy.** Ask each person before they write whether their text may be published anonymously in the repository and the thesis. Give them a code `ext-01`, `ext-02`, … in the order they join; do not store their names in the repository. Texts must not contain personal data; replace any by hand-picked test values *before* labelling, and note that in `notes`.
- **Material.** One card per task: a screenshot of the sample-app screen in its start state and a goal in plain words ("Doğru bilgilerle giriş yapılabildiğini test edin"). Do not show logical names, this guideline or our example sentences, and do not phrase the goal with the keywords' verbs, so that the writer is not primed.
- **Collecting.** Copy each text exactly as written, typos included (trim surrounding white space only). One text per card and person. The labeller assigns `style`, `tags` and `scenario`: outsider texts for the same card with identical gold share a scenario, others get their own.
- **Dropping.** A text that needs something out of scope (§6.7), refers to a control that does not exist, or cannot be labelled without guessing is not added. Count dropped texts and their reasons in the #57 task note.

**Brief to hand out (Turkish):**

> AYNA, masaüstü uygulamalarının testlerini Türkçe açıklamalardan otomatik test adımlarına çeviren bir araç. Sizden, gösterilen ekranda yapılacak kısa bir testi kendi cümlelerinizle anlatmanızı istiyoruz.
>
> - Her kartta bir ekran görüntüsü ve bir test amacı var.
> - Testi, bilgisayar başında oturan bir arkadaşınıza ne yapacağını anlatır gibi yazın: hangi adımları hangi sırayla yapacağını ve sonunda ekranda ne görmesi gerektiğini.
> - Girilecek değerleri ve beklenen mesajları ekranda göründüğü gibi tam yazın; isterseniz tırnak içinde.
> - Üslup serbest: tek cümle, madde madde ya da kısa notlar olabilir. Doğru ya da yanlış yazım yoktur.
> - Çift tıklama, klavye kısayolu, sürükleme ve "3 saniye bekle" gibi sabit beklemeler kullanmayın.
> - Adınızı ve kişisel bilgilerinizi yazmayın. Metniniz anonim olarak bir araştırma veri setinde ve bitirme tezinde yayımlanabilir.

## 9. Reviewer checklist

Every pair is labelled by one person and reviewed by another before it is merged.

- [ ] The text is natural Turkish a tester could have written (team), or unchanged from the writer (outsider).
- [ ] The gold does exactly what the text asks: no missing and no extra steps, in execution order (§6.1).
- [ ] Implicit actions are expanded and coordinated targets split (§6.2).
- [ ] Each target is the control the text means; keyword and property fit its control type (§6.3).
- [ ] Values and expected texts are verbatim; Select values are item texts (§6.4).
- [ ] Team pairs: a value whose end could read as a suffix is quoted, and no bare value has a suffix glued to it (§4.4). Outsider pairs: the reading of such a value is in `notes`.
- [ ] Every check-box Click changes the box from its start state, and `notes` gives that state (§6.8).
- [ ] Property, operator and boolean expected follow §4.2; `timeoutMs` only where the text gives a limit, on the right step (§4.3).
- [ ] `scenarioType`, `scenario`, `style` and `tags` are right; variants of a scenario have identical gold.
- [ ] Nothing out of scope (§6.7); no personal data.
- [ ] A positive team scenario would pass on the app version (§6.4).
- [ ] `check_pairs.py` passes.

For #57, have both labellers label 20 **outsider** pairs independently and report the share with identical gold, as a check that these rules make the gold reproducible. Team pairs would agree by construction: their writer had the gold in mind.

## 10. Checking the set

`check_pairs.py` needs only `jsonschema`, so the ai module's virtual environment works (from the repository root):

```
ai/.venv/bin/python eval/nl/check_pairs.py               # this folder; exit 1 on any problem
ai/.venv/bin/python eval/nl/check_pairs.py --min-styles 0   # while a type has fewer than 3 styles
```

It prints pairs per app and scenario type with the styles used, then every problem as `file:line: [code] message`. Besides the two schemas (the `style`, `tags`, `scenarioType` and `origin` values are closed lists there) it checks unique ids and texts, id prefixes, the app version, targets in the object list, keyword and property against control type, Select values against `items`, values present in the text, no suffix glued to a bare value in team pairs (§4.4), a start state in `notes` for every check-box Click (§6.8), the type rules of §3, identical gold within a scenario, no scenario on both sides of the held-out split, the held-out hash and at least three styles per type. The ai CI job runs it through `ai/tests/test_nl_dataset.py` until `eval/` has its own CI job (#122).
