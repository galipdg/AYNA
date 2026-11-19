import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, it } from 'node:test'
import {
  documentFrom,
  draftsFrom,
  fitsTarget,
  GRID_CONTROL_TYPES,
  localProblems,
  move,
  newDraft,
  parseSeconds,
  renamedTargets,
  secondsText,
  ROW_CONTROL_TYPES,
  serverProblems,
  STEP_SCHEMA_VERSION,
  targetTypes,
  withRenamedTargets,
  withTimeoutsIn,
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
const documentOf = (c: Case) => c.document ?? { version: STEP_SCHEMA_VERSION, steps: [c.step] }

describe('step rows', () => {
  it('turn a stored document into rows and back without a change', () => {
    assert.deepEqual(documentFrom(draftsFrom(example, 'tr-TR')), example)
    // Every valid case, rows of step schema 0.2 included (#205).
    for (const c of cases.valid) {
      const document = documentOf(c) as StepDocument
      assert.deepEqual(documentFrom(draftsFrom(document, 'tr-TR')), document, c.name)
    }
  })

  it('keep the row when SelectRow becomes a row check and back (#205)', () => {
    const row = { ...newDraft(), target: 'main.customerGrid', rowBy: 'value' as const }
    const selected = {
      ...row,
      keyword: 'SelectRow' as const,
      rowValue: 'Yılmaz',
      rowColumn: 'Soyad',
    }
    assert.deepEqual(documentFrom([selected]).steps, [
      {
        keyword: 'SelectRow',
        target: 'main.customerGrid',
        row: { value: 'Yılmaz', column: 'Soyad' },
      },
    ])
    const listed = { ...selected, keyword: 'Verify' as const, property: 'rowExists' as const }
    assert.deepEqual(documentFrom([listed]).steps[0].checkpoint, {
      property: 'rowExists',
      operator: 'equals',
      expected: true,
      row: { value: 'Yılmaz', column: 'Soyad' },
    })
    // rowCount reads no row and no column; an empty row column means any column.
    const counted = { ...listed, property: 'rowCount' as const, expectedCount: ' 2 ', column: 'Ad' }
    assert.deepEqual(documentFrom([counted]).steps[0].checkpoint, {
      property: 'rowCount',
      operator: 'equals',
      expected: 2,
    })
    const anyColumn = { ...selected, rowColumn: '' }
    assert.deepEqual(documentFrom([anyColumn]).steps[0].row, { value: 'Yılmaz' })
  })

  it('send a cell check with its row, its column and any text operator', () => {
    const cell = {
      ...newDraft(),
      keyword: 'Verify' as const,
      target: 'main.customerGrid',
      property: 'cell' as const,
      operator: 'notEquals' as const,
      rowIndex: '1',
      column: 'Şehir',
    }
    const { checkpoint } = documentFrom([cell]).steps[0]
    assert.deepEqual(checkpoint, {
      property: 'cell',
      operator: 'notEquals',
      expected: '',
      row: { index: 1 },
      column: 'Şehir',
    })
    assert.deepEqual(validateSteps(documentFrom([cell])), [])
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

  it('show "wait up to" with the language\'s decimal separator, and read both back (#206)', () => {
    assert.equal(secondsText(2500, 'tr-TR'), '2,5')
    assert.equal(secondsText(2500, 'en-GB'), '2.5')
    assert.equal(secondsText(1, 'tr-TR'), '0,001')
    // No grouping: Turkish "1.000" would read back as one second.
    assert.equal(secondsText(1_000_000, 'tr-TR'), '1000')
    for (const locale of ['tr-TR', 'en-GB']) {
      for (const ms of [0, 1, 250, 2500, 20000, 1_000_000]) {
        assert.equal(parseSeconds(secondsText(ms, locale)), ms, `${ms} in ${locale}`)
      }
    }
    const stored: StepDocument = {
      version: STEP_SCHEMA_VERSION,
      steps: [{ keyword: 'Click', target: 'login.okButton', timeoutMs: 2500 }],
    }
    assert.equal(draftsFrom(stored, 'tr-TR')[0].timeout, '2,5')
    assert.equal(draftsFrom(stored, 'en-GB')[0].timeout, '2.5')
  })

  it('rewrite "wait up to" numbers in a new language and leave the rest as typed', () => {
    const rows = ['2,5', '20', '', '2s'].map((timeout) => ({ ...newDraft(), timeout }))
    const english = withTimeoutsIn(rows, 'en-GB')
    assert.deepEqual(
      english.map((draft) => draft.timeout),
      ['2.5', '20', '', '2s'],
    )
    assert.equal(english[1], rows[1], 'an unchanged row stays the same object')
    assert.deepEqual(documentFrom(english), documentFrom(rows))
    assert.deepEqual(
      withTimeoutsIn(english, 'tr-TR').map((draft) => draft.timeout),
      ['2,5', '20', '', '2s'],
    )
  })

  it('carry an element renamed in the Repository into the rows (#206)', () => {
    const before = [
      { id: 'a', name: 'login.okButton' },
      { id: 'b', name: 'login.user' },
      { id: 'c', name: 'login.cancel' },
    ]
    const after = [
      { id: 'a', name: 'login.submit' },
      { id: 'b', name: 'login.user' },
      { id: 'd', name: 'login.new' },
    ]
    const renames = renamedTargets(before, after)
    assert.deepEqual([...renames], [['login.okButton', 'login.submit']])
    // Two names swapped in one reload are both carried, not chained.
    const swapped = renamedTargets(before.slice(0, 2), [
      { id: 'a', name: 'login.user' },
      { id: 'b', name: 'login.okButton' },
    ])
    const rows = ['login.okButton', 'login.user', 'login.cancel', ''].map((target) => ({
      ...newDraft(),
      target,
    }))
    assert.deepEqual(
      withRenamedTargets(rows, renames).map((draft) => draft.target),
      ['login.submit', 'login.user', 'login.cancel', ''],
    )
    assert.deepEqual(
      withRenamedTargets(rows, swapped).map((draft) => draft.target),
      ['login.user', 'login.okButton', 'login.cancel', ''],
    )
  })

  it('write the version of the schema file, the one the server checks', () => {
    assert.equal(STEP_SCHEMA_VERSION, read('step.schema.json').properties.version.const)
    assert.equal(documentFrom([]).version, STEP_SCHEMA_VERSION)
    assert.equal(example.version, STEP_SCHEMA_VERSION)
  })

  it('keep a wait of 0 (check once) apart from an empty one (the run default)', () => {
    const verify = { keyword: 'Verify', target: 'login.okButton' } as const
    const checkpoint = { property: 'enabled', operator: 'equals', expected: true } as const
    const stored: StepDocument = {
      version: STEP_SCHEMA_VERSION,
      steps: [
        { ...verify, checkpoint, timeoutMs: 0 },
        { ...verify, checkpoint },
      ],
    }
    const drafts = draftsFrom(stored, 'tr-TR')
    assert.deepEqual(
      drafts.map((draft) => draft.timeout),
      ['0', ''],
    )
    assert.deepEqual(documentFrom(drafts), stored)
    assert.equal(documentFrom([{ ...drafts[1], timeout: '0' }]).steps[0].timeoutMs, 0)
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
    assert.deepEqual(validateSteps({ version: STEP_SCHEMA_VERSION, steps }), [
      { index: 0, code: 'target-missing' },
      { index: 1, code: 'value-empty' },
      { index: 2, code: 'value-too-long' },
      { index: 3, code: 'timeout-range' },
      { index: 4, code: 'checkpoint-invalid' },
      { index: 5, code: 'value-not-allowed' },
    ])
  })

  it('names the reason of each row step a user can get wrong in the editor (#205)', () => {
    const grid = { ...newDraft(), target: 'main.customerGrid' }
    const selectRow = { ...grid, keyword: 'SelectRow' as const }
    const check = { ...grid, keyword: 'Verify' as const }
    const drafts = [
      selectRow, // no row number yet
      { ...selectRow, rowIndex: 'first' },
      { ...selectRow, rowIndex: '0' },
      { ...selectRow, rowIndex: '100001' },
      { ...selectRow, rowBy: 'value' as const, rowColumn: 'Soyad' }, // a column but no text
      { ...check, property: 'cell' as const, rowIndex: '1' }, // no column
      { ...check, property: 'cell' as const, column: 'Ad' }, // no row
      { ...check, property: 'rowExists' as const, rowIndex: '1.5' },
      { ...check, property: 'rowCount' as const }, // no count
      { ...check, property: 'rowCount' as const, expectedCount: 'two' },
      { ...check, property: 'rowCount' as const, expectedCount: '100001' },
    ]
    assert.deepEqual(validateSteps(documentFrom(drafts)), [
      { index: 0, code: 'row-missing' },
      { index: 1, code: 'row-invalid' },
      { index: 2, code: 'row-invalid' },
      { index: 3, code: 'row-invalid' },
      { index: 4, code: 'row-missing' },
      { index: 5, code: 'column-missing' },
      { index: 6, code: 'row-missing' },
      { index: 7, code: 'row-invalid' },
      { index: 8, code: 'count-invalid' },
      { index: 9, code: 'count-invalid' },
      { index: 10, code: 'count-invalid' },
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
    assert.deepEqual(localProblems([step], [{ name: 'login.okButton' }]), [])
    assert.deepEqual(localProblems([step], []), [{ index: 0, code: 'target-unknown' }])
  })

  it('marks a row action on an element that is not a table or list (#205)', () => {
    const objects = [
      { name: 'login.okButton', controlType: 'Button' },
      { name: 'main.customerGrid', controlType: 'DataGrid' },
      { name: 'settings.languageList', controlType: 'List' },
      { name: 'main.oldGrid' }, // control type never captured
    ]
    const selectRow = { ...step, keyword: 'SelectRow' as const }
    const cell = { ...step, keyword: 'Verify' as const, property: 'cell' as const }
    const count = { ...cell, property: 'rowCount' as const }
    const drafts = [
      selectRow,
      { ...selectRow, target: 'settings.languageList' },
      { ...selectRow, target: 'main.oldGrid' },
      cell,
      { ...cell, target: 'settings.languageList' },
      { ...cell, target: 'main.customerGrid' },
      count,
      { ...count, target: 'settings.languageList' },
      step, // Click works on any element
    ]
    assert.deepEqual(localProblems(drafts, objects), [
      { index: 0, code: 'target-not-rows' },
      { index: 3, code: 'target-not-grid' },
      { index: 4, code: 'target-not-grid' },
      { index: 6, code: 'target-not-rows' },
    ])
  })
})

describe('targetTypes', () => {
  it('offers grids and lists for rows, grids for a cell, anything otherwise', () => {
    const draft = newDraft()
    assert.equal(targetTypes(draft), undefined)
    assert.equal(targetTypes({ ...draft, keyword: 'SelectRow' }), ROW_CONTROL_TYPES)
    const verify = { ...draft, keyword: 'Verify' as const }
    assert.equal(targetTypes(verify), undefined)
    assert.equal(targetTypes({ ...verify, property: 'cell' }), GRID_CONTROL_TYPES)
    assert.equal(targetTypes({ ...verify, property: 'rowExists' }), ROW_CONTROL_TYPES)
    assert.equal(targetTypes({ ...verify, property: 'rowCount' }), ROW_CONTROL_TYPES)
    // A row property chosen before switching to Click does not narrow Click's elements.
    assert.equal(targetTypes({ ...draft, property: 'cell' }), undefined)
  })

  it('offers an element only when its control type is known to fit', () => {
    assert.ok(fitsTarget(undefined, undefined))
    assert.ok(fitsTarget(ROW_CONTROL_TYPES, 'List'))
    assert.ok(fitsTarget(GRID_CONTROL_TYPES, 'Table'))
    assert.ok(!fitsTarget(GRID_CONTROL_TYPES, 'List'))
    assert.ok(!fitsTarget(ROW_CONTROL_TYPES, undefined))
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
