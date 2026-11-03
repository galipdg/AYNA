# Client UI language: Turkish and English, chosen by the user

- Date: 2026-11-03
- Status: Proposed (#185) — the choice of both languages was made by the team on 2026-11-03; the rules below wait for the #185 PR review
- Deciders: Galip, Ömerfaruk, Hasan
- Issues: #185 · RS NFR-17 / TBD-2 (galip) · advisor question Q4 (#19) · NFR-16

## Context
The RS left the client's language open (TBD-2, NFR-17). Testers at HAVELSAN may prefer
Turkish, while the advisor, the course and the TestComplete comparison read English. Test data
(step values, expected values, NL descriptions) is Turkish whatever the UI language (NFR-16).
The client runs on a closed network, so the texts must ship with it, and the team did not want a
new dependency for this.

## Options considered
1. Turkish only — fits the users; the English material (report, demo for the advisor) would need translating screenshots.
2. English only — what the code had; testers who do not read English are left out.
3. Both, chosen by the user — chosen; costs a second dictionary and a test that keeps them in step.
4. An i18n library (i18next, FormatJS) — plurals and ICU messages for free, but a new dependency for about 300 texts in two languages whose plurals the code already handles.

## Decision
- The client offers **Turkish and English**. The user switches in the top bar, in Settings and on the screens before login; the switch applies at once and is saved in the machine's `settings.json` (`language`).
- **First run** (nothing saved): the operating system's first preferred language if it is Turkish or English, otherwise **Turkish** (`languageFor`, `client/src/shared/language.ts`).
- **No library.** Texts live in `client/src/renderer/src/i18n/en.ts` and `tr.ts` with the same keys; TypeScript checks the shape and `i18n.test.ts` fails when a text, a key or an argument differs, or when a Turkish text is still English.
- **Dates and numbers** follow the language: `tr-TR`, and `en-GB` for English (day-month order and a 24-hour clock, as the users expect). Coordinates, ids, DPI and pixel sizes stay plain.
- **Server messages** stay English on the server. The client maps the messages it knows (problem-details `detail` and field messages) to the current language, and shows any other message as sent. The table is `SERVER_MESSAGES` in `client/src/renderer/src/strings.ts`, with one real example of each in the test.
- **Test data is never translated**, upper-cased or changed (NFR-16), and no Turkish suffix is put after a value in a text.

## Consequences
- Every new text needs both languages; the test catches a missing one.
- Changing a server message the client maps breaks only the mapping (the message is then shown as sent); the test examples have to follow the server's wording.
- The agent's failure detail (exit code, last stderr line) and the agent's own error messages are diagnostics and stay as sent.
- RS NFR-17 / TBD-2 must say "Turkish and English, chosen by the user" (galip).
- Revisit if a third language or real plural rules are needed: that is when a library pays off.
