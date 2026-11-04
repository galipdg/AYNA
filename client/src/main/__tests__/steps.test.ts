import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, it } from 'node:test'
import {
  documentFrom,
  draftsFrom,
  localProblems,
  move,
  newDraft,
  parseSeconds,
  serverProblems,
  type StepDocument,
} from '../../shared/steps.ts'
import { validateSteps } from '../testCases.ts'

// The editor's row model (#38) and the step schema check, against the shared examples of
// schemas/step.schema.json (#13).

const schemas = join(import.meta.dirname, '..', '..', '..', '..', 'schemas')
const read = (...path: string[]) => JSON.parse(readFileSync(join(schemas, ...path), 'utf8'))

const example: StepDocument = read('examples', 'step', 'login-and-customer.json')

interface Case {
  name: string
  rule?: string
  document?: unknown
  step?: unknown
}
const cases = read('examples', 'step', 'cases.json') as { valid: Case[]; invalid: Case[] }
const documentOf = (c: Case) => c.document ?? { version: '0.1', steps: [c.step] }

describe('step rows', () => {
  it('turn a stored document into rows and back without a change', () => {
    assert.deepEqual(documentFrom(draftsFrom(example)), example)
    for (const c of cases.valid) {
      const document = documentOf(c) as StepDocument
      assert.deepEqual(documentFrom(draftsFrom(document)), document, c.name)
    }
  })

  it('send only the fields the action uses, and keep the others for a switch back', () => {
    const typed = { ...newDraft(), keyword: 'Type' as const, target: 'login.userInput', value: 'a' }
    const clicked = { ...typed, keyword: 'Click' as const }
    assert.deepEqual(documentFrom([clicked]).steps, [
      { keyword: 'Click', target: 'login.userInput' },
    ])
    assert.deepEqual(documentFrom([{ ...clicked, keyword: 'Type' }]).steps, [
      { keyword: 'Type', target: 'login.userInput', value: 'a' },
    ])
  })

  it('keep an empty text for Type (it clears the box)', () => {
    const step = { ...newDraft(), keyword: 'Type' as const, target: 'login.userInput' }
    assert.deepEqual(documentFrom([step]).steps[0].value, '')
    assert.deepEqual(validateSteps(documentFrom([step])), [])
  })

  it('check a true/false property with "equals" whatever operator was chosen for text', () => {
    const step = {
      ...newDraft(),
      keyword: 'Verify' as const,
      target: 'login.okButton',
      property: 'enabled' as const,
      operator: 'contains' as const,
      expectedFlag: false,
    }
    assert.deepEqual(documentFrom([step]).steps[0].checkpoint, {
      property: 'enabled',
      operator: 'equals',
      expected: false,
    })
  })

  it('read "wait up to" in seconds, with a decimal point or comma', () => {
    assert.equal(parseSeconds(''), undefined)
    assert.equal(parseSeconds(' 20 '), 20000)
    assert.equal(parseSeconds('2,5'), 2500)
    assert.equal(parseSeconds('0.001'), 1)
    assert.equal(parseSeconds('2s'), null)
    assert.equal(parseSeconds('-1'), null)
    assert.equal(parseSeconds('1.0001'), null)
  })

  it('move a step up and down', () => {
    assert.deepEqual(move(['a', 'b', 'c'], 0, 2), ['b', 'c', 'a'])
    assert.deepEqual(move(['a', 'b', 'c'], 2, 0), ['c', 'a', 'b'])
    assert.deepEqual(move(['a', 'b', 'c'], 0, -1), ['a', 'b', 'c'])
  })
})

describe('validateSteps', () => {
  it('accepts every valid example', () => {
    assert.deepEqual(validateSteps(example), [])
    for (const c of cases.valid) assert.deepEqual(validateSteps(documentOf(c)), [], c.name)
  })

  it('refuses every invalid example', () => {
    for (const c of cases.invalid) {
      const problems = validateSteps(documentOf(c))
      assert.ok(problems.length > 0, c.name)
      // A single-step case is reported on that step, not on the document.
      if (c.step)
        assert.ok(
          problems.every((p) => p.index === 0),
          c.name,
        )
    }
  })

  it('names the reason of each step a user can get wrong in the editor', () => {
    const steps = [
      { keyword: 'Click' },
      { keyword: 'Select', target: 'customer.cityComboBox', value: '' },
      { keyword: 'Type', target: 'login.userInput', value: 'x'.repeat(1001) },
      { keyword: 'Click', target: 'login.okButton', timeoutMs: 600001 },
      { keyword: 'Verify', target: 'login.status', checkpoint: { property: 'name' } },
      { keyword: 'Click', target: 'login.okButton', value: 'x' },
    ]
    assert.deepEqual(validateSteps({ version: '0.1', steps }), [
      { index: 0, code: 'target-missing' },
      { index: 1, code: 'value-empty' },
      { index: 2, code: 'value-too-long' },
      { index: 3, code: 'timeout-range' },
      { index: 4, code: 'checkpoint-invalid' },
      { index: 5, code: 'value-not-allowed' },
    ])
  })
})

describe('localProblems', () => {
  const step = { ...newDraft(), target: 'login.okButton' }

  it('marks a wait that is not a number of seconds', () => {
    assert.deepEqual(localProblems([{ ...step, timeout: 'soon' }], null), [
      { index: 0, code: 'timeout-number' },
    ])
  })

  it('marks an element that is not in the repository, once the list is loaded', () => {
    assert.deepEqual(localProblems([step], null), [])
    assert.deepEqual(localProblems([step], new Set(['login.okButton'])), [])
    assert.deepEqual(localProblems([step], new Set()), [{ index: 0, code: 'target-unknown' }])
  })
})

describe('serverProblems', () => {
  it('puts the server’s refused fields on their steps', () => {
    assert.deepEqual(
      serverProblems([
        {
          path: '$.steps[2].target',
          message: "No repository object named 'login.gone' in this application",
        },
        { path: '$.steps[0].id', message: 'Step 1 is not a step of this test' },
        { path: '$', message: 'Expected a step document {version, steps}' },
      ]),
      [
        { index: -1, code: 'invalid', message: 'Expected a step document {version, steps}' },
        { index: 0, code: 'invalid', message: 'Step 1 is not a step of this test' },
        { index: 2, code: 'target-unknown' },
      ],
    )
  })
})
