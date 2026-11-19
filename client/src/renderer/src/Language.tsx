import { createContext, useContext } from 'react'
import { LANGUAGES, type Language } from '../../shared/language.ts'
import Icon from './Icons.tsx'
import Menu from './Menu.tsx'
import { languageNames, strings } from './strings.ts'

export interface LanguageState {
  language: Language
  /** Shows the client in `language` at once and saves the choice for later runs. */
  choose(language: Language): void
  /** The last choice could not be saved; it still applies until the client closes. */
  saveFailed: boolean
}

export const LanguageContext = createContext<LanguageState>({
  language: 'tr',
  choose: () => undefined,
  saveFailed: false,
})

/** The languages as a pair of buttons, each named in its own language (#185). */
export function LanguageChoice() {
  const { language, choose, saveFailed } = useContext(LanguageContext)
  return (
    <>
      <ul className="choice-list" aria-label={strings.languageTitle}>
        {LANGUAGES.map((option) => (
          <li key={option}>
            <button
              type="button"
              lang={option}
              className={option === language ? 'selected' : undefined}
              aria-pressed={option === language}
              onClick={() => choose(option)}
            >
              {languageNames[option]}
            </button>
          </li>
        ))}
      </ul>
      {saveFailed && (
        <p className="field-error" role="alert">
          {strings.languageFailed}
        </p>
      )}
    </>
  )
}

/** The top bar's language menu: "TR ▾" / "EN ▾". */
export default function LanguageMenu({ align = 'end' }: { align?: 'start' | 'end' }) {
  const { language } = useContext(LanguageContext)
  return (
    <Menu
      title={strings.languageTitle}
      align={align}
      label={
        <>
          {language.toUpperCase()}
          <Icon name="chevron" />
        </>
      }
    >
      {() => (
        <div className="menu-body">
          <p className="menu-title">{strings.languageTitle}</p>
          <LanguageChoice />
          <p className="hint">{strings.languageHint}</p>
        </div>
      )}
    </Menu>
  )
}
