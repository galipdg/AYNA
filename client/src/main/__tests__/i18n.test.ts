import assert from 'node:assert/strict'
import { afterEach, describe, it } from 'node:test'
import { CHECK_TIMEOUT_MS, REQUEST_TIMEOUT_MS } from '../../shared/api.ts'
import { LANGUAGES } from '../../shared/language.ts'
import {
  dictionaries,
  formatDate,
  formatTime,
  serverText,
  setStringsLanguage,
  strings,
} from '../../renderer/src/strings.ts'

// The renderer's texts (#185) are plain data, so they are tested here with the other Node tests.

type Tree = { [key: string]: unknown }

/** Every leaf of a dictionary as `path → value`, e.g. `nav.spy → 'Object Spy'`. */
function leaves(tree: Tree, prefix = ''): Map<string, unknown> {
  const result = new Map<string, unknown>()
  for (const [key, value] of Object.entries(tree)) {
    if (typeof value === 'object' && value !== null) {
      for (const [path, leaf] of leaves(value as Tree, `${prefix}${key}.`)) result.set(path, leaf)
    } else {
      result.set(`${prefix}${key}`, value)
    }
  }
  return result
}

/** Same in both languages on purpose: names, examples and UIA terms. */
const SAME_IN_EVERY_LANGUAGE = new Set([
  'appName',
  'settingsPlatform',
  'serverUrlPlaceholder',
  'appTechnologyPlaceholder',
  'controlTypes.Pane',
  'spyProperties.automationId',
  'spyProperties.dpi',
  'repoNamePlaceholder',
  'tokenNamePlaceholder',
])

describe('UI texts', () => {
  const english = leaves(dictionaries.en)

  for (const language of LANGUAGES) {
    const texts = leaves(dictionaries[language])

    it(`${language}: has exactly the keys of English, each of the same kind`, () => {
      assert.deepEqual([...texts.keys()].sort(), [...english.keys()].sort())
      for (const [path, value] of english) {
        const other = texts.get(path)
        assert.equal(typeof other, typeof value, path)
        if (typeof value === 'function') {
          assert.equal((other as () => string).length, value.length, `${path}: arguments`)
        }
      }
    })

    it(`${language}: no text is empty, and a text with values says them all`, () => {
      for (const [path, value] of texts) {
        if (typeof value === 'string') {
          assert.ok(value.trim(), path)
          continue
        }
        // An array works as a number, a string and a list of strings alike.
        const args = Array.from({ length: (value as () => string).length }, (_, i) => [`v${i}`])
        const text = (value as (...a: unknown[]) => string)(...args)
        assert.equal(typeof text, 'string', path)
        assert.ok(text.trim(), path)
        assert.doesNotMatch(text, /undefined|NaN|\[object/, path)
        args.forEach((_, i) => assert.ok(text.includes(`v${i}`), `${path} drops value ${i}`))
      }
    })
  }

  it('tr: every text is translated, apart from names and examples', () => {
    const turkish = leaves(dictionaries.tr)
    for (const [path, value] of english) {
      if (typeof value !== 'string' || path === 'locale') continue
      if (SAME_IN_EVERY_LANGUAGE.has(path)) assert.equal(turkish.get(path), value, path)
      else assert.notEqual(turkish.get(path), value, `${path} is still English`)
    }
  })

  it('tr: follows the glossary spellings (#203)', () => {
    for (const [path, value] of leaves(dictionaries.tr)) {
      const text =
        typeof value === 'function'
          ? (value as (...a: unknown[]) => string)(['v0'], ['v1'], ['v2'], ['v3'])
          : String(value)
      // TDK writes "öğe"; "ajan" reads as "spy" next to Nesne Gözcüsü, so the agent is "Aracı".
      assert.doesNotMatch(text, /(^|[^\p{L}])[öÖ]ge/u, `${path}: öğe`)
      assert.doesNotMatch(text, /(^|[^\p{L}])ajan/iu, `${path}: Aracı`)
      assert.doesNotMatch(text, /"/, `${path}: Turkish quotes are “…”`)
    }
  })

  it('timeout texts name the timeouts the main process uses', () => {
    setStringsLanguage('en')
    assert.ok(strings.requestErrors.timeout.includes(`within ${REQUEST_TIMEOUT_MS / 1000} seconds`))
    const check = strings.connectionErrors.timeout('http://x')
    assert.ok(check.includes(`within ${CHECK_TIMEOUT_MS / 1000} seconds`))
    setStringsLanguage('tr')
    assert.ok(strings.loginErrors.timeout.includes(`${REQUEST_TIMEOUT_MS / 1000} saniye içinde`))
  })
})

describe('dates and numbers follow the language', () => {
  afterEach(() => setStringsLanguage('tr'))

  it('formats counts with the language’s digit grouping', () => {
    setStringsLanguage('tr')
    assert.match(strings.spyCaptured('10:00', undefined, 3031, 1250), /3\.031 öğe/)
    setStringsLanguage('en')
    assert.match(strings.spyCaptured('10:00', undefined, 3031, 1250), /3,031 elements in 1,250 ms/)
  })

  it('formats dates and times in the language (en-GB for English)', () => {
    const iso = '2026-11-03T09:15:07Z'
    setStringsLanguage('tr')
    assert.match(formatDate(iso), /^3 Kas 2026$/)
    assert.match(formatTime(iso), /^\d\d:15:07$/)
    setStringsLanguage('en')
    assert.match(formatDate(iso), /^3 Nov 2026$/)
    assert.match(formatTime(iso), /^\d\d:15:07$/)
  })

  it('shows a value that is not a date as it is', () => {
    assert.equal(formatDate('soon'), 'soon')
    assert.equal(formatTime('soon'), 'soon')
  })
})

describe('serverText', () => {
  afterEach(() => setStringsLanguage('tr'))

  // One real message per known case, as the server sends it (server/src/main/java/...).
  const examples: [string, (t: (typeof strings)['serverMessages']) => string][] = [
    ['Log in first: the request has no valid session or API token', (t) => t.logInFirst],
    ['Only admins may do this', (t) => t.adminsOnly],
    [
      "'username' must be 1 to 64 characters: letters a-z, digits, '.', '_' or '-'",
      (t) => t.usernameForm,
    ],
    ["'password' must be at least 8 characters", (t) => t.passwordShort('8')],
    ["'password' must be at most 72 bytes in UTF-8", (t) => t.passwordLong('72')],
    ['User name already taken: ayse', (t) => t.usernameTaken('ayse')],
    ['The last admin cannot become a tester', (t) => t.lastAdminTester],
    ['The last admin cannot be removed', (t) => t.lastAdminRemoved],
    ["'name' must not be blank", (t) => t.tokenNameBlank],
    ['Application already exists: Not Defteri', (t) => t.applicationExists('Not Defteri')],
    [
      'Version 1.0 already exists for application 6f1c2e9a-0000-4000-8000-000000000001',
      (t) => t.versionExists('1.0'),
    ],
    [
      'The logical name login.okButton is already used by repository object ' +
        '6f1c2e9a-0000-4000-8000-000000000002 in this application',
      (t) => t.elementNameTaken('login.okButton'),
    ],
    ['At least one primary property is needed to find the element', (t) => t.primaryNeeded],
    ['The repository object is not valid', (t) => t.objectInvalid],
    [
      'login.girisButton is used by 2 tests: Giriş çalışır, Login rejects empty password. ' +
        'Change those steps first',
      (t) => t.objectInUse('login.girisButton', '2', 'Giriş çalışır, Login rejects empty password'),
    ],
    [
      'login.okButton is used by 1 test: Login works. Change those steps first',
      (t) => t.objectInUse('login.okButton', '1', 'Login works'),
    ],
    ['Repository object not found: 6f1c2e9a-0000-4000-8000-000000000003', (t) => t.objectGone],
    [
      'A test with this name already exists in the application: Giriş çalışır',
      (t) => t.testNameTaken('Giriş çalışır'),
    ],
    ['Test not found: 6f1c2e9a-0000-4000-8000-000000000004', (t) => t.testGone],
    ['The steps do not match step schema 0.1', (t) => t.stepsRefused],
    ['The steps refer to unknown step ids or repository objects', (t) => t.stepsRefused],
    [
      'Step 6f1c2e9a-0000-4000-8000-000000000005 is not a step of this test',
      (t) => t.stepNotInTest,
    ],
  ]

  for (const language of LANGUAGES) {
    it(`${language}: maps every known server message`, () => {
      setStringsLanguage(language)
      for (const [message, expected] of examples) {
        assert.equal(serverText(message), expected(strings.serverMessages), message)
      }
    })
  }

  it('has an example for every known message', () => {
    const used = new Set<string>()
    const spy = new Proxy(dictionaries.en.serverMessages, {
      get(target, key: string) {
        used.add(key)
        return target[key as keyof typeof target]
      },
    })
    for (const [, expected] of examples) expected(spy)
    assert.deepEqual([...used].sort(), Object.keys(dictionaries.en.serverMessages).sort())
  })

  it('shows an unknown message as the server sent it', () => {
    const message = 'The snapshot does not match snapshot schema 0.1'
    assert.equal(serverText(message), message)
  })

  it('keeps Turkish test data in a message unchanged', () => {
    setStringsLanguage('tr')
    assert.equal(
      serverText('Application already exists: Şirket İçi Uygulama'),
      'Bu adda bir uygulama zaten var: Şirket İçi Uygulama.',
    )
  })
})
