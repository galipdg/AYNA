import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, it } from 'node:test'
import { matchCount, type PropertySet } from '../../shared/repository.ts'
import type { Snapshot } from '../../shared/snapshot.ts'

interface SeedObject {
  name: string
  snapshotElementId: string
  primary: PropertySet
  fallback: PropertySet
}

// `dev/` is plain JavaScript outside the type-checked tree, so it is loaded by URL.
const seedUrl = new URL('../../../dev/demo/seed.mjs', import.meta.url).href
const { repoObjects } = (await import(seedUrl)) as {
  repoObjects: (snapshot: Snapshot) => SeedObject[]
}

const snapshot: Snapshot = JSON.parse(
  readFileSync(
    join(import.meta.dirname, '..', '..', '..', '..', 'schemas', 'examples', 'snapshot', 'trial-login.json'),
    'utf8',
  ),
)
const objects = repoObjects(snapshot)

describe('demo seed objects (#207)', () => {
  it('finds its own element with each set in the trial window', () => {
    for (const { name, snapshotElementId, primary, fallback } of objects) {
      const own = snapshot.elements.filter((node) => node.id === snapshotElementId)
      for (const set of [primary, fallback]) {
        if (Object.keys(set).length === 0) continue
        assert.equal(matchCount(set, own), 1, `${name}: not its own element`)
        assert.equal(matchCount(set, snapshot.elements), 1, `${name}: ${JSON.stringify(set)}`)
      }
    }
  })

  it('gives a backup set to every element with a Name, and none to the status label', () => {
    const fallbacks = Object.fromEntries(objects.map((o) => [o.name, o.fallback]))
    assert.deepEqual(fallbacks['login.loginButton'], { name: 'Login', controlType: 'Button' })
    assert.deepEqual(fallbacks['login.statusLabel'], {})
    assert.equal(objects.filter((o) => Object.keys(o.fallback).length > 0).length, 4)
  })
})
