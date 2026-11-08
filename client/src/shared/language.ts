// The client's UI languages (#185). Test data is never translated, whatever the language (NFR-16).

export type Language = 'tr' | 'en'

export const LANGUAGES: readonly Language[] = ['tr', 'en']

export function isLanguage(value: unknown): value is Language {
  return LANGUAGES.includes(value as Language)
}

/**
 * The language of a first run, before the user has chosen one: the operating system's
 * first preferred language when it is Turkish or English, otherwise Turkish.
 * `systemLanguages` are BCP 47 tags such as `en-US` or `tr`.
 */
export function languageFor(systemLanguages: readonly string[]): Language {
  const primary = systemLanguages[0]?.split(/[-_]/)[0]?.toLowerCase()
  return isLanguage(primary) ? primary : 'tr'
}
