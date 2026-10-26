import assert from 'node:assert/strict'
import { mkdtemp, readdir, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { after, before, describe, it } from 'node:test'
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
    })
  })

  it('survives a restart: what is saved is loaded again', async () => {
    const file = join(dir, 'nested', 'settings.json')
    const saved = { serverUrl: 'http://ayna-server:8080', applicationId: 'app-1' }
    await saveSettings(file, saved)
    assert.deepEqual(await loadSettings(file), saved)
    assert.deepEqual(await readdir(join(dir, 'nested')), ['settings.json'])
    assert.match(await readFile(file, 'utf8'), /\n$/)
  })

  it('falls back to the defaults for malformed or wrongly typed content', async () => {
    const file = join(dir, 'bad.json')
    for (const content of ['{not json', 'null', '[]', '{"serverUrl": 42, "applicationId": 7}']) {
      await writeFile(file, content)
      assert.deepEqual(await loadSettings(file), { serverUrl: null, applicationId: null }, content)
    }
  })

  it('reads a file written before applicationId existed', async () => {
    const file = join(dir, 'old.json')
    await writeFile(file, '{"serverUrl": "http://ayna-server:8080"}')
    assert.deepEqual(await loadSettings(file), {
      serverUrl: 'http://ayna-server:8080',
      applicationId: null,
    })
  })
})

describe('withServer', () => {
  const current = { serverUrl: 'http://a:8080', applicationId: 'app-1' }

  it('keeps the chosen application when reconnecting to the same server', () => {
    assert.deepEqual(withServer(current, 'http://a:8080'), current)
  })

  it('clears the chosen application when the server changes', () => {
    assert.deepEqual(withServer(current, 'http://b:8080'), {
      serverUrl: 'http://b:8080',
      applicationId: null,
    })
  })
})
