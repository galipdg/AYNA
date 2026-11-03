import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import type { ElementDescriptor } from '../../shared/element.ts'
import type { TreeNode } from '../../shared/snapshot.ts'
import {
  ancestorIds,
  elementMatches,
  foldText,
  parentMap,
  searchTree,
  visibleRows,
} from '../../shared/tree.ts'

function node(id: string, element: ElementDescriptor, children: TreeNode[] = []): TreeNode {
  return { id, element, children }
}

// window
// ├─ group "Giriş"
// │  ├─ Edit "Kullanıcı adı" (AutomationId userName)
// │  └─ Button "Giriş yap"
// └─ MenuBar
//    └─ MenuItem "Dosya"
const tree = node('w', { controlType: 'Window', name: 'Login' }, [
  node('g', { controlType: 'Group', name: 'Giriş' }, [
    node('e', { controlType: 'Edit', name: 'Kullanıcı adı', automationId: 'userName' }),
    node('b', { controlType: 'Button', name: 'Giriş yap' }),
  ]),
  node('m', { controlType: 'MenuBar' }, [node('mi', { controlType: 'MenuItem', name: 'Dosya' })]),
])

const ids = (rows: { node: TreeNode }[]) => rows.map((row) => row.node.id)

describe('foldText', () => {
  it('ignores case and the Turkish dotted and dotless i', () => {
    assert.equal(foldText('KULLANICI'), foldText('kullanıcı'))
    assert.equal(foldText('İptal'), 'iptal')
    assert.equal(foldText('ID'), 'id')
  })
})

describe('elementMatches', () => {
  it('matches name, control type and AutomationId', () => {
    const edit = { controlType: 'Edit', name: 'Kullanıcı adı', automationId: 'userName' }
    assert.ok(elementMatches(edit, 'kullanici'))
    assert.ok(elementMatches(edit, 'edit'))
    assert.ok(elementMatches(edit, 'USERNAME'))
    assert.ok(!elementMatches(edit, 'button'))
  })

  it('matches the plain type label when given', () => {
    const label = (type: string) => (type === 'Edit' ? 'Text box' : type)
    assert.ok(elementMatches({ controlType: 'Edit' }, 'text box', label))
    assert.ok(!elementMatches({ controlType: 'Edit' }, 'text box'))
  })

  it('matches everything for a blank query', () => {
    assert.ok(elementMatches({}, '  '))
  })
})

describe('parentMap and ancestorIds', () => {
  it('lists the ancestors nearest first', () => {
    const parents = parentMap(tree)
    assert.equal(parents.get('w'), null)
    assert.deepEqual(ancestorIds('e', parents), ['g', 'w'])
    assert.deepEqual(ancestorIds('w', parents), [])
  })
})

describe('visibleRows', () => {
  it('shows children of open nodes only, in tree order with depth', () => {
    const rows = visibleRows(tree, new Set(['w', 'g']))
    assert.deepEqual(ids(rows), ['w', 'g', 'e', 'b', 'm'])
    assert.deepEqual(
      rows.map((row) => row.depth),
      [0, 1, 2, 2, 1],
    )
    assert.equal(rows.find((row) => row.node.id === 'm')!.open, false)
  })

  it('marks leaves as not open', () => {
    const rows = visibleRows(tree, new Set(['w', 'g', 'e']))
    assert.equal(rows.find((row) => row.node.id === 'e')!.open, false)
  })

  it('handles a deep tree without recursion', () => {
    let deep = node('leaf', {})
    const open = new Set<string>()
    for (let i = 0; i < 20000; i++) {
      deep = node(`n${i}`, {}, [deep])
      open.add(`n${i}`)
    }
    assert.equal(visibleRows(deep, open).length, 20001)
  })
})

describe('searchTree', () => {
  it('returns null for an empty query', () => {
    assert.equal(searchTree(tree, ' '), null)
  })

  it('shows matches with their ancestors, all open, whatever was folded', () => {
    const result = searchTree(tree, 'dosya')!
    assert.deepEqual([...result.matches], ['mi'])
    const rows = visibleRows(tree, new Set(), result.shown)
    assert.deepEqual(ids(rows), ['w', 'm', 'mi'])
  })

  it('finds several matches across branches', () => {
    const result = searchTree(tree, 'giriş')!
    assert.deepEqual([...result.matches].sort(), ['b', 'g'])
    assert.deepEqual(ids(visibleRows(tree, new Set(), result.shown)), ['w', 'g', 'b'])
  })
})
