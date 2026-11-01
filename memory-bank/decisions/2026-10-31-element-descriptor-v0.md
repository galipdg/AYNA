# Element descriptor v0: the properties, the priority, and how a label is found

- Date: 2026-10-31
- Status: Proposed (#11)
- Deciders: Galip, Ömerfaruk, Hasan
- Issues: #11 · consumed by #12, #25, #43, #49, #73 · evidence from #6, #9, #161

## Context
Every later piece of AYNA compares two elements: playback resolves a repository object against
a live window, healing scores candidates, change-impact walks from an element to the tests that
use it. They can only agree if "an element" means one thing. Three facts shape it:

- **What UI Automation actually gives us** (#6, four pilot apps): `AutomationId` is present for
  35 % of KeePass 2's interactive elements, 73 % of HandBrake's, 100 % of KeePassXC's — but only
  10 % of KeePassXC's are unique, and 96 % of Notepad++'s are framework-generated numbers.
  `Name` covers 57–88 %. `LabeledBy` is filled by Qt only (12 % of KeePassXC's).
- **Two consumers already exist**: `heal/scorer.py` reads `automationId`, `name`, `controlType`,
  `className`, `bounds`, `parentPath`, `siblingIndex`, `nearestLabel`, `windowTitle` (plus `dpi`
  in PR #166), and `schemas/healing-proposal.schema.json` freezes that list as `scoredElement`.
- **A derived property is only stable if the rule is** (galip, #159 review): healing recomputes
  the label from a stored snapshot (#43), so a label derived one way at capture time and another
  way at healing time looks to the scorer like a label that changed.

## Decision

### 1. The descriptor
`schemas/element.schema.json` (`urn:ayna:schema:element`, version `0.1`) and
`agent/ayna_agent/model.py`. camelCase in JSON, snake_case in Python. Every property is
optional and a blank string is never stored: no framework fills them all in. The set is a
**superset of `scoredElement`**, so a stored element can always be rebuilt into a scorer input:

| Read from UIA | Computed by the agent | Captured, not scored in v0 |
|---|---|---|
| `automationId`, `name`, `controlType`, `className`, `frameworkId`, `bounds`, `dpi`, `enabled`, `offscreen`, `windowTitle`, `nativeWindowHandle` | `parentPath`, `siblingIndex`, `nearestLabel`, `nearestLabelSource` | `helpText`, `accessKey` |

`helpText` and `accessKey` are stored although nothing scores them, because **capture is
expensive and scoring is cheap**: #161 measured a walk at 12 ms per element, so a property we
failed to capture costs a new run of the application, while a property we captured and do not
use costs bytes.

### 2. `automationId` is stored whole, never clipped
The 200-character clip in the #6 dumps is an artefact of the dump. Qt builds the id from the
whole object chain, and 25 of KeePassXC's 84 elements exceed 200 characters; clipping turns
distinct ids into collisions.

### 3. A written-down priority, and a list that never identifies anything
Following ROBULA+ (#10 [5]), which shows that an explicit priority plus an explicit black list
beats both "always the id" and "always the path":

- **Primary, best first:** `automationId` (only when it is not framework-generated),
  `name`, `nearestLabel`, `className`, `parentPath`.
- **Never used to identify** (`model.NEVER_MATCH`, with the reason in the code): `bounds`
  (absolute geometry; only the scorer's DIP location/area/shape compare it), `dpi`,
  `nativeWindowHandle` (a new handle every run), `frameworkId` (the same for every element of
  an application), `enabled` and `offscreen` (state, not identity).
- **Generated ids** are whole-string digits, GUIDs, and a Qt dotted id whose *leaf* is a class
  name (`…QPushButton2`) — the case behind KeePassXC's 10 % uniqueness.

### 4. `parentPath` and `siblingIndex`
`parentPath` is the ancestors' **programmatic** control type names, root first, joined by `/`
(`Window/Pane/Group`); the element's own type is not in it, and an unreadable ancestor becomes
`?` so the depth survives. Never the localised name: a Turkish Windows reports `Pencere/Bölme`.
`siblingIndex` is the zero-based position among the parent's children in the raw view.

### 5. How `nearestLabel` is found — normative for #43
In order, with `nearestLabelSource` recording which rule answered:

1. **`labeledBy`** — the UIA `LabeledBy` relation, when it has text. The toolkit's own answer
   always wins.
2. **`geometric`** — the nearest label-like sibling (`Text` or `Group`) **to the left**, with
   vertical overlap, at most **48 device-independent pixels** away. Smaller gap wins; the lower
   `siblingIndex` breaks a tie.
3. **`parentRow`** — the same rule **one level up**, among the parent's siblings, because Qt and
   WinForms wrap each form row in a panel. One level only: climbing further labels everything
   with the first text on the form.

Both constraints are measurements, not preferences, taken over the four #6 dumps and the trial
app (#9):

- **Only to the left.** All seven KeePassXC elements with a `LabeledBy` relation are labelled
  from the left, at **13 DIP**; the trial app's two labelled inputs sit at 6 and 10 DIP. A rule
  that also accepts a label *above* was implemented and tested, and it produced only errors: it
  gives the trial app's "Remember me" check box and "Login" button the password field's label
  (6 DIP above them), and labels a KeePass 2 combo box "20 ch.". Left-first reproduces
  `LabeledBy` 7/7 where distance-first reproduces it 6/7.
- **48 DIP.** The ceiling sits 3.7× above the largest true gap (13 DIP) and 5.4× below the
  nearest false pairing measured in those five applications (261 DIP). In DIP, not pixels, so
  the rule holds at every display scaling.

A later version may add an "above" rule for web-style layouts if it also requires the two left
edges to line up; v0 does not need it, because every pilot and the sample app are desktop forms.

## Consequences
- **#12 (snapshot)** emits these descriptors; its budget and property set come from #161 (plain
  properties and `LabeledBy`, no pattern probes).
- **#43 (healing features)** must use the rules in §4 and §5 unchanged, and may read
  `nearestLabelSource` to tell a changed label from a changed method.
- **#25 / the graph model**: `Element` in `docs/graph-model.md` lists `automationId`, `name`,
  `controlType`, `className`, `bounds`, `snapshotId`; it needs the rest of this set, and
  **`dpi` in particular** — without it a stored target is converted one-sidedly and scores 0.33
  against itself (measured on PR #166). Raised in omer's inbox.
- **`healing-proposal.schema.json`** has `additionalProperties: false` on `scoredElement` and no
  `dpi`, so a proposal carrying the `dpi` that PR #166 now uses would be invalid. It needs the
  same addition; that is galip's file and his call.
- **#23 (win32 fallback)** gets `nativeWindowHandle` and `className` for the 41 % of Notepad++'s
  interactive elements that have neither id nor Name.
- The schema is a `schemas/` contract: changing it after this needs an ADR and all three
  owners' approval, and `version` goes to `0.2`.

## Alternatives considered
- **Reuse `scoredElement` as the descriptor.** Rejected: it has no `dpi`, no state, no
  `frameworkId` and no provenance for the label, and it is shaped for one consumer.
- **snake_case in JSON** (as the issue text writes the fields). Rejected: every other contract
  boundary in the repo is camelCase, and the scorer and the graph model already read camelCase.
- **Store a UIA RuntimeId.** Rejected: it is session-scoped, so it identifies nothing across
  runs — the same reason `nativeWindowHandle` is captured but never matched.
- **Compute the label at healing time only.** Rejected: healing would have to re-walk the live
  window for every candidate, and the stored and live labels would come from different rules,
  which is exactly what galip's #159 review warned about.
