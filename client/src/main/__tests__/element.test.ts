import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, it } from 'node:test'
import { ELEMENT_FIELDS, formatBounds, formatDpi, windowDescriptor } from '../../shared/element.ts'

const schemaPath = join(
  import.meta.dirname,
  '..',
  '..',
  '..',
  '..',
  'schemas',
  'element.schema.json',
)
const schema = JSON.parse(readFileSync(schemaPath, 'utf8')) as {
  properties: { version: { const: string } }
  $defs: { element: { properties: Record<string, { enum?: string[] }> } }
}

describe('ELEMENT_FIELDS', () => {
  it('lists every field of the element schema exactly once', () => {
    assert.equal(schema.properties.version.const, '0.1')
    assert.deepEqual(
      [...ELEMENT_FIELDS].sort(),
      Object.keys(schema.$defs.element.properties).sort(),
    )
  })

  it('knows every nearestLabelSource the schema allows', () => {
    // Mirrors the union in ElementDescriptor and the labels in strings.ts.
    assert.deepEqual(schema.$defs.element.properties.nearestLabelSource.enum, [
      'labeledBy',
      'geometric',
      'parentRow',
    ])
  })
})

describe('windowDescriptor', () => {
  const win = {
    handle: 395942,
    title: 'Untitled - Notepad',
    className: 'Notepad',
    processId: 7316,
    processName: 'notepad.exe',
    bounds: [320, 180, 960, 660] as [number, number, number, number],
  }

  it('maps what the window list reports', () => {
    assert.deepEqual(windowDescriptor(win), {
      name: 'Untitled - Notepad',
      windowTitle: 'Untitled - Notepad',
      className: 'Notepad',
      bounds: [320, 180, 960, 660],
      nativeWindowHandle: 395942,
    })
  })

  it('leaves out blank strings, as the schema requires', () => {
    assert.deepEqual(windowDescriptor({ ...win, title: '  ', className: '' }), {
      bounds: [320, 180, 960, 660],
      nativeWindowHandle: 395942,
    })
  })
})

describe('formatting', () => {
  it('adds the size to bounds', () => {
    assert.equal(formatBounds([320, 180, 960, 660]), '320, 180, 960, 660 (640 × 480)')
    assert.equal(formatBounds([-1920, 0, -960, 540]), '-1920, 0, -960, 540 (960 × 540)')
  })

  it('adds the scaling to DPI', () => {
    assert.equal(formatDpi(96), '96 (100 %)')
    assert.equal(formatDpi(144), '144 (150 %)')
    assert.equal(formatDpi(120), '120 (125 %)')
  })
})
