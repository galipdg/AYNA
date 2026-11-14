import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import {
  contentSecurityPolicy,
  isAllowedNavigation,
  isAllowedRequest,
  isTrustedSender,
  reportWebPreferences,
  secureWebPreferences,
} from '../security.ts'

const DEV = 'http://localhost:5173'

describe('contentSecurityPolicy', () => {
  for (const dev of [false, true]) {
    it(`allows no remote origin (dev=${dev})`, () => {
      const csp = contentSecurityPolicy({ dev })
      assert.doesNotMatch(csp, /https?:|wss?:|\*/)
      assert.match(csp, /default-src 'none'/)
      assert.match(csp, /script-src 'self'/)
      assert.match(csp, /object-src 'none'/)
    })
  }

  it('allows inline scripts and styles only in dev', () => {
    assert.doesNotMatch(contentSecurityPolicy(), /unsafe-inline/)
    assert.match(contentSecurityPolicy({ dev: true }), /unsafe-inline/)
  })

  it('never allows eval', () => {
    assert.doesNotMatch(contentSecurityPolicy({ dev: true }), /unsafe-eval/)
  })
})

describe('isAllowedRequest', () => {
  it('allows bundled files, data URLs and DevTools', () => {
    assert.ok(isAllowedRequest('file:///app/out/renderer/index.html'))
    assert.ok(isAllowedRequest('data:image/png;base64,AAAA'))
    assert.ok(isAllowedRequest('devtools://devtools/bundled/inspector.html'))
  })

  it('blocks remote URLs, with or without a dev server', () => {
    for (const url of [
      'https://fonts.googleapis.com/css?family=Roboto',
      'https://cdn.jsdelivr.net/npm/react',
      'http://example.com/',
      'wss://example.com/socket',
    ]) {
      assert.equal(isAllowedRequest(url), false, url)
      assert.equal(isAllowedRequest(url, DEV), false, url)
    }
  })

  it('allows the dev server only when one is running', () => {
    assert.ok(isAllowedRequest(`${DEV}/src/main.jsx`, DEV))
    assert.ok(isAllowedRequest('ws://localhost:5173/', DEV))
    assert.equal(isAllowedRequest(`${DEV}/src/main.jsx`), false)
    assert.equal(isAllowedRequest('http://localhost:8080/api', DEV), false)
  })

  it('rejects malformed URLs', () => {
    assert.equal(isAllowedRequest('not a url'), false)
  })
})

describe('isAllowedNavigation', () => {
  const entry = 'file:///app/out/renderer/index.html'

  it('allows only the entry page', () => {
    assert.ok(isAllowedNavigation(entry, entry))
    assert.ok(isAllowedNavigation(`${DEV}/`, `${DEV}/`))
    assert.equal(isAllowedNavigation('https://example.com/', entry), false)
    assert.equal(isAllowedNavigation('file:///etc/passwd', entry), false)
    assert.equal(isAllowedNavigation('https://example.com/', `${DEV}/`), false)
  })
})

describe('isTrustedSender', () => {
  const entry = 'file:///app/out/renderer/index.html'

  it("accepts only the entry page's frame", () => {
    assert.ok(isTrustedSender(entry, entry))
    assert.ok(isTrustedSender(`${DEV}/`, DEV))
    assert.equal(isTrustedSender('file:///app/out/renderer/other.html', entry), false)
    assert.equal(isTrustedSender('https://example.com/', entry), false)
  })

  it('rejects a destroyed frame', () => {
    assert.equal(isTrustedSender(undefined, entry), false)
  })
})

describe('secureWebPreferences', () => {
  it('isolates the renderer from Node', () => {
    const prefs = secureWebPreferences('/app/out/preload/index.js')
    assert.equal(prefs.contextIsolation, true)
    assert.equal(prefs.nodeIntegration, false)
    assert.equal(prefs.sandbox, true)
    assert.equal(prefs.webSecurity, true)
    assert.equal(prefs.webviewTag, false)
    assert.equal(prefs.preload, '/app/out/preload/index.js')
  })
})

describe('reportWebPreferences', () => {
  it('gives the report window no script, no Node and no bridge', () => {
    const prefs = reportWebPreferences()
    assert.equal(prefs.javascript, false)
    assert.equal(prefs.contextIsolation, true)
    assert.equal(prefs.nodeIntegration, false)
    assert.equal(prefs.sandbox, true)
    assert.equal('preload' in prefs, false)
  })
})
