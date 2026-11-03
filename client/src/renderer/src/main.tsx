import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import type { Language } from '../../shared/language.ts'
import App from './App.tsx'
import { setStringsLanguage } from './strings.ts'
import './styles.css'

const root = document.getElementById('root')
if (!root) throw new Error('#root element missing from index.html')

// The language is known before the first render, so no screen shows in the wrong one.
window.ayna
  .getLanguage()
  .catch((): Language => 'tr')
  .then((language) => {
    setStringsLanguage(language)
    document.documentElement.lang = language
    createRoot(root).render(
      <StrictMode>
        <App initialLanguage={language} />
      </StrictMode>,
    )
  })
