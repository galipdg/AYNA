import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  HISTORY_LIMIT,
  TYPING_GAP_MS,
  historyCommand,
  mapHistory,
  record,
  redo,
  startHistory,
  undo,
} from '../../shared/history.ts'
import { newDraft, withStoredIds } from '../../shared/steps.ts'

test('undo and redo walk through the changes', () => {
  let history = startHistory('a')
  history = record(history, 'b')
  history = record(history, 'c')
  history = undo(history)
  assert.equal(history.present, 'b')
  history = undo(history)
  assert.equal(history.present, 'a')
  history = redo(history)
  assert.equal(history.present, 'b')
  history = redo(history)
  assert.equal(history.present, 'c')
})

test('undo and redo with nothing to do change nothing', () => {
  const history = startHistory('a')
  assert.equal(undo(history), history)
  assert.equal(redo(history), history)
})

test('a new change drops what could be redone', () => {
  let history = record(startHistory('a'), 'b')
  history = undo(history)
  history = record(history, 'c')
  assert.deepEqual(history.future, [])
  assert.equal(redo(history).present, 'c')
})

test('a change that changed nothing is not recorded', () => {
  const rows = ['a']
  const history = startHistory(rows)
  assert.equal(record(history, rows), history)
})

test('the oldest changes go past the limit', () => {
  let history = startHistory(0)
  for (let i = 1; i <= HISTORY_LIMIT + 5; i++) history = record(history, i)
  assert.equal(history.past.length, HISTORY_LIMIT)
  assert.equal(history.past[0], 5)
})

test('keystrokes in one field undo as one change', () => {
  let history = startHistory('')
  history = record(history, 'a', 'row:value', 1000)
  history = record(history, 'ay', 'row:value', 1100)
  history = record(history, 'ayş', 'row:value', 1200)
  assert.equal(history.past.length, 1)
  assert.equal(undo(history).present, '')
})

test('a pause starts a new change', () => {
  let history = record(startHistory(''), 'a', 'row:value', 1000)
  history = record(history, 'ab', 'row:value', 1000 + TYPING_GAP_MS)
  assert.equal(history.past.length, 2)
})

test('typing in another field starts a new change', () => {
  let history = record(startHistory(''), 'a', 'row:value', 1000)
  history = record(history, 'b', 'row:timeout', 1100)
  assert.equal(history.past.length, 2)
})

test('another kind of change ends the typing', () => {
  let history = record(startHistory(''), 'a', 'row:value', 1000)
  history = record(history, 'b', undefined, 1100)
  history = record(history, 'c', 'row:value', 1200)
  assert.equal(history.past.length, 3)
})

test('typing after an undo starts a new change', () => {
  let history = record(startHistory(''), 'a', 'row:value', 1000)
  history = undo(history)
  history = record(history, 'b', 'row:value', 1100)
  assert.equal(history.past.length, 1)
  assert.equal(undo(history).present, '')
})

test('mapHistory changes every state', () => {
  const history = undo(record(record(startHistory(1), 2), 3))
  const doubled = mapHistory(history, (n) => n * 2)
  assert.deepEqual(doubled.past, [2])
  assert.equal(doubled.present, 4)
  assert.deepEqual(doubled.future, [6])
})

test('a saved row gets its id, and a row gone from the server loses it', () => {
  const kept = { ...newDraft(), id: 'old-id' }
  const added = newDraft()
  const deleted = { ...newDraft(), id: 'deleted-id' }
  const ids = new Map([
    [kept.key, 'old-id'],
    [added.key, 'new-id'],
  ])
  const rows = withStoredIds([kept, added, deleted], ids)
  assert.deepEqual(
    rows.map((row) => row.id),
    ['old-id', 'new-id', undefined],
  )
})

const keys = { key: 'z', ctrlKey: false, metaKey: false, shiftKey: false, altKey: false }

test('the undo and redo keys', () => {
  assert.equal(historyCommand({ ...keys, ctrlKey: true }), 'undo')
  assert.equal(historyCommand({ ...keys, metaKey: true }), 'undo')
  assert.equal(historyCommand({ ...keys, key: 'Z', ctrlKey: true, shiftKey: true }), 'redo')
  assert.equal(historyCommand({ ...keys, key: 'Z', metaKey: true, shiftKey: true }), 'redo')
  assert.equal(historyCommand({ ...keys, key: 'y', ctrlKey: true }), 'redo')
})

test('other keys are not undo or redo', () => {
  assert.equal(historyCommand(keys), null)
  assert.equal(historyCommand({ ...keys, key: 's', ctrlKey: true }), null)
  assert.equal(historyCommand({ ...keys, ctrlKey: true, altKey: true }), null)
  assert.equal(historyCommand({ ...keys, key: 'y', ctrlKey: true, shiftKey: true }), null)
})
