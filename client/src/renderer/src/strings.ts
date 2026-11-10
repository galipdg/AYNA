import type { RepoObjectError, ReportResult, TestError, UsersError } from '../../shared/api.ts'
import type { Language } from '../../shared/language.ts'
import { en, type Strings } from './i18n/en.ts'
import { tr } from './i18n/tr.ts'

export type { Strings }

export const dictionaries: Record<Language, Strings> = { tr, en }

/** Language names in their own language, so each is found whatever the current one is. */
export const languageNames: Record<Language, string> = { tr: 'Türkçe', en: 'English' }

/**
 * The texts of the current language. Read at render time (`strings.x`), never copied into a
 * module constant, so a language change shows once the tree re-renders (App does that).
 */
export let strings: Strings = tr
export let language: Language = 'tr'

export function setStringsLanguage(next: Language) {
  language = next
  strings = dictionaries[next]
}

/** A date such as `2026-11-03T09:15:00Z` in the current language: "3 Nov 2026" / "3 Kas 2026". */
export function formatDate(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleDateString(strings.locale, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

/** A time of day in the current language, with seconds: "14:05:09". */
export function formatTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleTimeString(strings.locale)
}

/**
 * Messages the server sends (problem-details `detail` and field messages, RFC 9457) that the
 * client knows; they are shown in the current language. Patterns follow the server's texts in
 * `server/src/main/java/com/ayna/server/**`; `i18n.test.ts` holds one real example of each.
 */
const SERVER_MESSAGES: [RegExp, (texts: Strings['serverMessages'], match: string[]) => string][] = [
  [/^Log in first\b/, (t) => t.logInFirst],
  [/^Only admins may do this$/, (t) => t.adminsOnly],
  [/^'username' must be 1 to 64 characters/, (t) => t.usernameForm],
  [/^'password' must be at least (\d+) characters$/, (t, m) => t.passwordShort(m[1])],
  [/^'password' must be at most (\d+) bytes/, (t, m) => t.passwordLong(m[1])],
  [/^User name already taken: (.+)$/, (t, m) => t.usernameTaken(m[1])],
  [/^The last admin cannot become a tester$/, (t) => t.lastAdminTester],
  [/^The last admin cannot be removed$/, (t) => t.lastAdminRemoved],
  [/^'name' must not be blank$/, (t) => t.tokenNameBlank],
  [/^Application already exists: (.+)$/, (t, m) => t.applicationExists(m[1])],
  [/^Version (.+) already exists for application \S+$/, (t, m) => t.versionExists(m[1])],
  [
    /^The logical name (\S+) is already used by repository object/,
    (t, m) => t.elementNameTaken(m[1]),
  ],
  [/^At least one primary property is needed/, (t) => t.primaryNeeded],
  [/^The repository object is not valid$/, (t) => t.objectInvalid],
  [
    /^(\S+) is used by (\d+) tests?: (.+)\. Change those steps first$/,
    (t, m) => t.objectInUse(m[1], m[2], m[3]),
  ],
  [/^Repository object not found: /, (t) => t.objectGone],
  [
    /^A test with this name already exists in the application: (.+)$/,
    (t, m) => t.testNameTaken(m[1]),
  ],
  [/^Test not found: /, (t) => t.testGone],
  [
    /^The steps (?:do not match step schema|refer to unknown step ids or repository objects)/,
    (t) => t.stepsRefused,
  ],
  [/^Step \S+ is not a step of this test$/, (t) => t.stepNotInTest],
]

/** A server message in the current language when the client knows it, otherwise as sent. */
export function serverText(message: string): string {
  for (const [pattern, text] of SERVER_MESSAGES) {
    const match = pattern.exec(message)
    if (match) return text(strings.serverMessages, [...match])
  }
  return message
}

/** The server's own message when it sent one (e.g. which field is wrong), else ours. */
export function usersErrorText(error: UsersError): string {
  return error.detail ? serverText(error.detail) : strings.usersErrors[error.reason]
}

/** The server's message when it sent one, then the refused fields; else ours. */
export function repoObjectErrorText(error: RepoObjectError): string[] {
  const main = error.detail ? serverText(error.detail) : strings.repoViewErrors[error.reason]
  return [main, ...(error.fields ?? []).map((field) => serverText(field.message))]
}

/** A run's or step's length: "850 ms", "2.5 s" / "2,5 sn", "3 min 4 s" / "3 dk 4 sn". */
export function formatDuration(ms: number): string {
  if (ms < 1000) return strings.durationMs(String(ms))
  if (ms < 60_000) {
    const seconds = (ms / 1000).toLocaleString(strings.locale, { maximumFractionDigits: 1 })
    return strings.durationSeconds(seconds)
  }
  const total = Math.round(ms / 1000)
  return strings.durationMinutes(String(Math.floor(total / 60)), String(total % 60))
}

/** The server's message when it sent one, else ours. */
export function runsErrorText(error: Exclude<ReportResult, { ok: true }>): string {
  return 'detail' in error && error.detail && error.reason !== 'write-failed'
    ? serverText(error.detail)
    : strings.runsErrors[error.reason]
}

/** The server's message when it sent one, else ours. Step fields are shown on their rows. */
export function testErrorText(error: TestError): string {
  return error.detail ? serverText(error.detail) : strings.testsErrors[error.reason]
}

/** A control type in plain words ("Edit" → "Text box"). */
export function controlTypeLabel(controlType: string | undefined): string {
  if (controlType === undefined) return strings.spyUnknownControlType
  return strings.controlTypes[controlType] ?? controlType
}
