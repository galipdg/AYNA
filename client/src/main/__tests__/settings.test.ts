import assert from 'node:assert/strict'
import { mkdtemp, readdir, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { after, before, describe, it } from 'node:test'
import { loadSettings, saveSettings } from '../settings.ts'

describe('settings', () => {
  let dir: string

  before(async () => {
    dir = await mkdtemp(join(tmpdir(), 'ayna-settings-'))
  })

  after(() => rm(dir, { recursive: true, force: true }))

  it('returns the defaults when there is no file yet (first run)', async () => {
    assert.deepEqual(await loadSettings(join(dir, 'missing.json')), { serverUrl: null })
  })

  it('survives a restart: what is saved is loaded again', async () => {
    const file = join(dir, 'nested', 'settings.json')
    await saveSettings(file, { serverUrl: 'http://ayna-server:8080' })
    assert.deepEqual(await loadSettings(file), { serverUrl: 'http://ayna-server:8080' })
    assert.deepEqual(await readdir(join(dir, 'nested')), ['settings.json'])
    assert.match(await readFile(file, 'utf8'), /\n$/)
  })

  it('falls back to the defaults for malformed or wrongly typed content', async () => {
    const file = join(dir, 'bad.json')
    for (const content of ['{not json', 'null', '[]', '{"serverUrl": 42}']) {
      await writeFile(file, content)
      assert.deepEqual(await loadSettings(file), { serverUrl: null }, content)
    }
  })
})
