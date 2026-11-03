import assert from 'node:assert/strict'
import { mkdtemp, readdir, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { after, before, describe, it } from 'node:test'
import { languageFor } from '../../shared/language.ts'
import { loadSettings, saveSettings, withServer } from '../settings.ts'

describe('settings', () => {
  let dir: string

  before(async () => {
    dir = await mkdtemp(join(tmpdir(), 'ayna-settings-'))
  })

  after(() => rm(dir, { recursive: true, force: true }))

  it('returns the defaults when there is no file yet (first run)', async () => {
    assert.deepEqual(await loadSettings(join(dir, 'missing.json')), {
      serverUrl: null,
      applicationId: null,
      language: null,
    })
  })

  it('survives a restart: what is saved is loaded again', async () => {
    const file = join(dir, 'nested', 'settings.json')
    const saved = {
      serverUrl: 'http://ayna-server:8080',
      applicationId: 'app-1',
      language: 'en' as const,
    }
    await saveSettings(file, saved)
    assert.deepEqual(await loadSettings(file), saved)
    assert.deepEqual(await readdir(join(dir, 'nested')), ['settings.json'])
    assert.match(await readFile(file, 'utf8'), /\n$/)
  })

  it('falls back to the defaults for malformed or wrongly typed content', async () => {
    const file = join(dir, 'bad.json')
    const contents = [
      '{not json',
      'null',
      '[]',
      '{"serverUrl": 42, "applicationId": 7, "language": "de"}',
    ]
    for (const content of contents) {
      await writeFile(file, content)
      assert.deepEqual(
        await loadSettings(file),
        { serverUrl: null, applicationId: null, language: null },
        content,
      )
    }
  })

  it('reads a file written before applicationId and language existed', async () => {
    const file = join(dir, 'old.json')
    await writeFile(file, '{"serverUrl": "http://ayna-server:8080"}')
    assert.deepEqual(await loadSettings(file), {
      serverUrl: 'http://ayna-server:8080',
      applicationId: null,
      language: null,
    })
  })
})

describe('withServer', () => {
  const current = { serverUrl: 'http://a:8080', applicationId: 'app-1', language: 'tr' as const }

  it('keeps the chosen application when reconnecting to the same server', () => {
    assert.deepEqual(withServer(current, 'http://a:8080'), current)
  })

  it('clears the chosen application, not the language, when the server changes', () => {
    assert.deepEqual(withServer(current, 'http://b:8080'), {
      serverUrl: 'http://b:8080',
      applicationId: null,
      language: 'tr',
    })
  })
})

describe('languageFor (first run)', () => {
  it('uses the system language when it is Turkish or English', () => {
    assert.equal(languageFor(['tr-TR', 'en-US']), 'tr')
    assert.equal(languageFor(['en-US', 'tr-TR']), 'en')
    assert.equal(languageFor(['en']), 'en')
    assert.equal(languageFor(['EN_gb']), 'en')
  })

  it('falls back to Turkish for any other language, or none', () => {
    assert.equal(languageFor(['de-DE', 'en-US']), 'tr')
    assert.equal(languageFor([]), 'tr')
    assert.equal(languageFor(['']), 'tr')
  })
})
