# AYNA client style guide

Draft for the #183 team review. One visual style for every client screen: layout, colours, type, components and words. Built with plain CSS custom properties in `client/src/renderer/src/styles.css`; no CSS framework, no web font, no icon font, nothing loaded from the network.

## 1 Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ TOP BAR  48 px · context: application, version · agent, language, user       │
├────────────┬─────────────────────────────────────────────────────────────────┤
│ NAV        │ PAGE HEADER  title · one-line help · page actions (right)       │
│ 200 px     ├─────────────────────────────────────────────────────────────────┤
│ (56 px     │ WORK AREA                                                       │
│ collapsed) │ panels side by side; each panel scrolls on its own              │
│            │                                                                 │
│ places     │ ┌ panel ──────────┐ ┌ panel ─────────────────────────────────┐  │
│            │ │ header          │ │ header                                 │  │
│            │ │ body (scrolls)  │ │ body (scrolls)                         │  │
│ ────────── │ │                 │ │                                        │  │
│ Users      │ │                 │ │ footer: actions                        │  │
│ Settings   │ └─────────────────┘ └────────────────────────────────────────┘  │
└────────────┴─────────────────────────────────────────────────────────────────┘
```

- **Window:** designed at 1280 × 720 (a 1920 × 1080 laptop at 150 %), minimum 960 × 600 (the main window's `minWidth`/`minHeight`). Below 1180 px wide the navigation collapses to icons with tooltips. Between 960 and about 1280 px every screen works, but a wide table may scroll sideways inside its panel: the step table of the Tests screen does below about 1280 px (34 px at 1180), less once the test list is dragged narrower. The minimum stays at 960 on purpose: a 1366 × 768 screen at 125 % is about 1090 px wide, so a 1280 minimum would push the window off it (#207).
- **The page never scrolls as a whole.** The top bar, navigation and page header stay; panels scroll inside.
- **Panels:** list panels 280–360 px wide, detail panels take the rest. The user can drag a panel edge; the width is kept per screen across restarts.
- **Before login** (server settings, login, first application choice) there is no shell: one centred card, 440 px wide, on the page background, with the AYNA name above it.
- **Dialogs** only for confirmations that destroy or change shared data ("Remove user", "Use this element"). Everything else happens in a panel.
- **Spacing:** a 4 px grid. Use 4, 8, 12, 16, 24, 32 only. Inside panels 16 px padding; between fields 16 px; between a label and its field 4 px.

## 2 Colours

Two themes that follow the operating system's light or dark setting (`prefers-color-scheme`). Every colour is a custom property; components use only the tokens, never raw hex values.

| Token | Use | Light | Dark |
|---|---|---|---|
| `--bg` | Page background behind panels | `#F5F6F8` | `#14171B` |
| `--surface` | Panels, cards, top bar, inputs | `#FFFFFF` | `#1C2025` |
| `--border` | Panel and field borders, dividers | `#D5DBE1` | `#343A42` |
| `--text` | Body text | `#1B1F24` | `#E6E9ED` |
| `--text-muted` | Hints, secondary labels, table headers | `#5B6573` | `#A3ACB7` |
| `--accent` | Main buttons, links, focus ring, running state | `#0B6E99` | `#5CB8E4` |
| `--on-accent` | Text on `--accent` | `#FFFFFF` | `#0A1A22` |
| `--selected` | Background of the chosen row or tree node | `#E3F1F8` | `#1F3846` |
| `--success` / `--success-soft` | Passed, saved, connected | `#1E7B34` / `#E7F4EA` | `#62C27E` / soft at 15 % |
| `--danger` / `--danger-soft` | Failed, errors, remove | `#B42318` / `#FDECEA` | `#F27B70` / soft at 15 % |
| `--warning` / `--warning-soft` | Needs review, restarting, partial capture | `#8A5A00` / `#FFF4DB` | `#E5B551` / soft at 15 % |

Contrast (WCAG 2.1, computed for this draft): every text colour above is at least 4.5 : 1 on `--surface`, `--bg` and `--selected` in both themes (lowest: light `--success` on `--selected` 4.6, dark `--danger` on `--selected` 4.6). White on light `--accent` is 5.7 : 1.

**Colour never carries meaning alone.** A status always has a word and a shape as well: ✓ Passed, ✕ Failed, ! Needs review, – Skipped, ● Running.

**Accent is rare.** One main button per panel at most; the rest are secondary. The Spy's on-screen outline stays red (`#E53935`, #24) because it must stand out on any application.

## 3 Type

System fonts only: `"Segoe UI", system-ui, -apple-system, sans-serif`. Values that the user may compare character by character (AutomationId, class name, window handle, token) use `ui-monospace, Consolas, monospace`, and only under Advanced.

| Role | Size / weight | Use |
|---|---|---|
| Page title | 20 px / 600 | One per page, in the page header |
| Panel title | 15 px / 600 | Panel headers, dialog titles |
| Body | 14 px / 400, line height 1.45 | Labels, text, buttons, fields |
| Small | 12.5 px / 400 | Hints, table headers, status bar, timestamps |
| Mono | 13 px | Advanced values only |

Sentence case everywhere ("Add to repository", not "Add To Repository"). No all-caps except the AYNA name.

## 4 Components

Each component has one class in `styles.css`. Screens compose them; they do not add their own colours or borders.

### Buttons

| Kind | Look | When |
|---|---|---|
| Main (`.btn-main`) | `--accent` fill, `--on-accent` text | The one action the panel exists for: Save, Connect, Log in, Run |
| Secondary (`.btn`) | `--surface` fill, `--border` outline | Every other action: Cancel, Refresh, Capture again, Export |
| Danger (`.btn-danger`) | `--danger` text and outline; filled only in its confirm dialog | Remove, Revoke, None of these |
| Quiet (`.btn-quiet`) | Text only, `--accent` | Inline actions inside lists and messages: Try again, Show on screen |

- Height 32 px, 6 px radius, label is a verb or verb phrase ("Add version", not "OK").
- While busy: the label changes to the -ing form ("Saving…") and the button is disabled; the rest of the form stays readable.
- A disabled button always has a tooltip that says why ("Choose an element first").

### Fields

```
Element name                          ← label above, 14 px
┌──────────────────────────────────┐
│ login.userNameInput              │  ← 32 px high, 6 px radius
└──────────────────────────────────┘
Write the screen, a dot, then the element.   ← hint, small, muted
✕ This name is already used by login.userName.   ← error replaces hint, --danger
```

- The label is always visible (no placeholder-only fields). Placeholders show an example, not an instruction.
- Validate when the user leaves the field or saves, not on every key.
- An error goes under its field and names the field's subject; the field gets a `--danger` border. The first wrong field gets focus on save.

### Panels

A panel has a header (title on the left, at most three secondary actions on the right), a body that scrolls, and an optional footer for the main action. Panels sit on `--bg` with a 1 px `--border` and 8 px radius, 8 px apart.

### Lists and trees

- Row height 32 px; the chosen row has `--selected` background and a 3 px `--accent` bar on its left edge.
- Up/Down move the choice, Enter opens, Left/Right fold tree nodes. The chosen row is scrolled into view.
- A list with more than about 15 items has a search field on top (filters as the user types, highlights the match).
- Long lists and trees (thousands of elements, #184) render only the visible rows.

### Tables

Header in small muted text, rows 36 px, numbers right-aligned, the first column is the thing's name and opens it. Sorting by clicking a header; the sorted column shows ▲ or ▼.

### Messages

| Kind | Where | Look |
|---|---|---|
| Field error | Under the field | `--danger` text with ✕ |
| Panel message | Top of the panel body | Soft background (`--danger-soft`, `--warning-soft`, `--success-soft`), icon, one or two sentences, optional quiet action ("Try again") |
| Page message | Under the page header | Same look, for problems with the whole screen (server unreachable, agent not running) |
| Confirmation | Short success text that stays until the next action, next to the button that caused it | `--success` with ✓ ("Saved login.okButton.") |

No pop-up toasts that vanish before they are read, and no `alert()`.

### Empty states

Every list, table and panel has one. Centred in the panel: one sentence that says why it is empty, one sentence or button that says what to do.

```
        No saved elements yet.
  Pick an element in the Object Spy and add it here.
              [ Open Object Spy ]
```

### Status pills

Small rounded label with icon and word: `● Ready`, `◌ Starting…`, `↻ Restarting (2 of 3)`, `✕ Not running`, `✓ Passed`, `✕ Failed`, `! Needs review`, `– Skipped`, `■ Stopped`.

### Advanced sections

A closed disclosure (`<details>`) at the bottom of a panel, labelled **Advanced**, with a one-line summary of what is inside. It holds technical properties (AutomationId, class name, framework, parent path, window handle, DPI) and raw values, shown by their UI Automation names. It is not only for test engineers: AutomationId, class name and parent path are often what AYNA finds an element by, so anyone fixing a "Find by" set works there. When a screen asks the user to change something inside it, such as a suggested "Find by" set that does not find exactly one element, the section opens by itself (#204). Otherwise it remembers whether it was open, per screen.

### Tooltips

On hover or keyboard focus after 500 ms. Use them to explain an internal term in one sentence, never for information the user needs to finish the task.

### Unavailable places

A navigation item whose screen is not built yet is shown in `--text-muted` with a small "Later" pill; clicking it opens a page that names the screen, what it will do and the issue that builds it. It never hides, so the advisor can see the whole product.

## 5 Wording rules

1. Write for a tester, not for a programmer. Use the glossary below; never show a JSON key, an HTTP status or a stack trace.
2. Buttons are verbs. Titles are nouns. Hints are one sentence.
3. Errors say what happened, which thing it concerns (URL, element name, step number, field) and what to do next: "Could not reach http://ayna-server:8080. Check the address and that the server is running."
4. Say "you" for the user and "AYNA" for the system. No "please", no "successfully", no exclamation marks.
5. Numbers carry units ("12 elements in 340 ms", "waits up to 10 s").
6. User data (test names, values, Turkish text) is shown exactly as typed, never translated, upper-cased or trimmed (NFR-16).
7. Every text lives in both `i18n/en.ts` and `i18n/tr.ts` (#185); `i18n.test.ts` fails when one is missing. Dates and numbers go through the current language (`formatDate`, `formatTime`, the dictionaries' `count`); coordinates, ids and px stay plain.

### Plain-language glossary

The UI word is what the user sees. The internal term may appear only under Advanced or in a tooltip. The Turkish column is what the client shows since #185, with the review points of #188–#191 applied in #203. Turkish follows TDK spelling (öğe) and uses typographic quotes “…”.

| Internal term | UI word (English) | UI word (Turkish) | Tooltip when needed |
|---|---|---|---|
| AUT, application under test | Application | Uygulama | |
| Application version | Version | Sürüm | "The build of the application you are testing." |
| Repository object | Saved element | Kayıtlı öğe | "An element of the application that tests use by its name." |
| Object repository | Repository | Nesne Deposu (in buttons and messages: depo, as in “Depoya ekle”) | |
| Logical name | Element name | Öğe adı | "Tests use this name, so they keep working when the screen changes." |
| Primary properties | Find by | Bununla bul | |
| Fallback properties | Backup | Yedek | "Tried when the Find-by properties no longer match." |
| Descriptor | Properties | Özellikler | |
| Snapshot | Capture | Yakalama | |
| UIA element | Element | Öğe | |
| Control type | Type | Tür | |
| Nearest label | Label next to it | Yanındaki etiket | |
| Spy group for a picked element (name, type, label, window) | What it is | Ne olduğu | For a saved element the group is "How AYNA finds it" / "AYNA bu öğeyi nasıl bulur" |
| `offscreen` = false | On screen | Ekranda | |
| UIA Name | Text | Metin | "UI Automation Name; for most controls, the visible text" |
| Control type DataGrid / DataItem | Data grid / Data item | Veri tablosu / Veri öğesi | |
| `RESOLVES_TO` versions of a saved element | Captured in versions | Yakalandığı sürümler | The edge records a capture the tester saved from, not a search of that version |
| Step keyword Click / Type / Select / Verify / Wait | Click / Type text / Choose item / Check / Wait for | Tıkla / Yaz / Listeden seç / Kontrol et / Bekle | Listeden seç: plain “seç” would also mean Click to the NL author |
| Checkpoint, Verify step | Check | Kontrol | |
| Checkpoint property name / value / enabled / visible / checked / selected | Text / Field content / Enabled / On screen / Checked / Selected | Metin / Alan içeriği / Etkin / Ekranda / İşaretli / Seçili | Text: "the text of a label or button"; Field content: "what is typed in a box" |
| Operator equals / notEquals / contains | is / is not / contains | eşittir / eşit değildir / içerir | |
| `timeoutMs` | Wait up to (s) | En fazla bekle (sn) | |
| Healing proposal | Repair suggestion | Onarım önerisi | "AYNA could not find the element and suggests similar ones. Nothing changes until you choose." |
| Candidate | Suggested element | Önerilen öğe | |
| Score / contribution | Match / why it matches | Benzerlik / neden benziyor | |
| Approve / reject | Use this element / None of these | Bu öğeyi kullan / Hiçbiri | |
| Change impact | Changes between versions | Sürümler arası değişiklikler | |
| Run status passed / failed / repairProposed / notRun / aborted | Passed / Failed / Needs review / Skipped / Stopped | Geçti / Başarısız / İnceleme bekliyor / Atlandı / Durduruldu | |
| Failure category element not found / unexpected window / assertion failed / timeout / search incomplete | Element not found / Unexpected window / Check failed / Took too long / Window too slow to search | Öğe bulunamadı / Beklenmeyen pencere / Kontrol başarısız / Çok uzun sürdü / Pencere zamanında taranamadı | |
| Agent | Agent | Aracı (not “ajan”, which reads as “spy”) | "The AYNA program on this computer that reads and drives the application." |
| API token | API token | API anahtarı | "Lets a CI server run tests without logging in." |

## 6 Icons

About a dozen 16 px inline SVGs, drawn with `currentColor` so they follow the theme: spy (crosshair), repository (stack), tests (list), runs (play), repairs (wrench), changes (two arrows), users, settings (gear), search, refresh, plus status marks ✓ ✕ ! ●. No icon library.

## 7 Keyboard

- Every action reachable by keyboard; visible focus ring (2 px `--accent`, 2 px offset).
- `Ctrl+F` focuses the current panel's search, `Esc` closes a dialog or cancels an edit, `Enter` runs the panel's main action.
- The global pick hotkey of the Spy (#24) is shown wherever picking is possible.
- `Ctrl+1`…`Ctrl+6` go to the navigation places in order.
