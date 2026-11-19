import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, it } from 'node:test'
import { ELEMENT_FIELDS } from '../../shared/element.ts'
import {
  IDENTIFYING_FIELDS,
  isGeneratedId,
  LOGICAL_NAME,
  logicalNameProblem,
  matchCount,
  objectsMatching,
  suggestUses,
} from '../../shared/repository.ts'
import type { Snapshot } from '../../shared/snapshot.ts'

const schemas = join(import.meta.dirname, '..', '..', '..', '..', 'schemas')
const trial: Snapshot = JSON.parse(
  readFileSync(join(schemas, 'examples', 'snapshot', 'trial-login.json'), 'utf8'),
)
const element = (id: string) => trial.elements.find((node) => node.id === id)!.element

describe('logical names', () => {
  it('uses the step schema pattern', () => {
    const step = JSON.parse(readFileSync(join(schemas, 'step.schema.json'), 'utf8'))
    assert.equal(LOGICAL_NAME.source, step.$defs.logicalName.pattern)
  })

  it('accepts screen.element and names what is wrong otherwise (SC-11)', () => {
    assert.equal(logicalNameProblem('login.userNameInput'), null)
    assert.equal(logicalNameProblem('  login.userNameInput '), null)
    assert.equal(logicalNameProblem('Login Button'), 'form')
    assert.equal(logicalNameProblem('login.user.name'), 'form')
    assert.equal(logicalNameProblem('none.noMatch'), 'reserved')
    assert.equal(logicalNameProblem('   '), 'blank')
  })
})

describe('isGeneratedId', () => {
  it('follows the agent rule: digits, GUIDs and Qt class-name leaves are generated', () => {
    assert.equal(isGeneratedId('12345'), true)
    assert.equal(isGeneratedId('3f2504e0-4f89-11d3-9a0c-0305e82c3301'), true)
    assert.equal(isGeneratedId('QApplication.mainWindow.QPushButton2'), true)
    assert.equal(isGeneratedId('form.1042'), true)
    assert.equal(isGeneratedId('QApplication.loginWindow.usernameInput'), false)
    assert.equal(isGeneratedId('btnOk'), false)
    assert.equal(isGeneratedId(''), false)
  })
})

describe('suggestUses', () => {
  it('keeps the never-matching descriptor fields out', () => {
    for (const field of [
      'bounds',
      'dpi',
      'nativeWindowHandle',
      'frameworkId',
      'enabled',
      'offscreen',
    ]) {
      assert.ok(!(IDENTIFYING_FIELDS as readonly string[]).includes(field), field)
    }
    assert.ok(
      IDENTIFYING_FIELDS.every((field) => (ELEMENT_FIELDS as readonly string[]).includes(field)),
    )
  })

  it('takes a unique AutomationId alone as primary and the rest of the priority as fallback (SC-10)', () => {
    assert.deepEqual(suggestUses(element('e8'), trial.elements), {
      automationId: 'primary',
      name: 'fallback',
      nearestLabel: 'fallback',
      className: 'fallback',
      parentPath: 'fallback',
      controlType: 'fallback',
      windowTitle: 'unused',
      siblingIndex: 'unused',
    })
  })

  it('adds properties to primary until only the element matches', () => {
    // e2 (the menu bar) and e3 (its item) are both named "System"; the parent path tells them apart.
    const uses = suggestUses(element('e3'), trial.elements)
    assert.equal(uses.name, 'primary')
    assert.equal(uses.parentPath, 'primary')
    assert.equal(uses.controlType, 'fallback')
    assert.equal(
      matchCount({ name: 'System', parentPath: 'Window/TitleBar/MenuBar' }, trial.elements),
      1,
    )
  })

  it('never suggests a generated AutomationId', () => {
    const uses = suggestUses({ automationId: '1042', name: 'OK', controlType: 'Button' }, [])
    assert.equal(uses.automationId, 'unused')
    assert.equal(uses.name, 'primary')
  })

  it('always suggests one primary property, even when the element is alone', () => {
    const only = [{ id: 'e0', parentId: null, element: { name: 'Main', controlType: 'Window' } }]
    assert.deepEqual(suggestUses(only[0].element, only), {
      name: 'primary',
      controlType: 'fallback',
    })
  })
})

describe('objectsMatching', () => {
  const saved = [
    {
      name: 'login.userNameInput',
      primary: { automationId: 'QApplication.loginWindow.usernameInput' },
    },
    { name: 'login.anyEdit', primary: { controlType: 'Edit' as const } },
    { name: 'login.passwordInput', primary: { nearestLabel: 'Password', controlType: 'Edit' } },
    { name: 'login.nothing', primary: {} },
  ]

  it('finds the objects whose every Find by value the element has', () => {
    assert.deepEqual(
      objectsMatching(saved, element('e8')).map((object) => object.name),
      ['login.userNameInput', 'login.anyEdit'],
    )
  })

  it('never matches an object without Find by properties', () => {
    assert.deepEqual(objectsMatching(saved.slice(3), element('e8')), [])
  })
})
