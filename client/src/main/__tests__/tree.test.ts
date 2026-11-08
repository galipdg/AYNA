import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import type { ElementDescriptor } from '../../shared/element.ts'
import type { TreeNode } from '../../shared/snapshot.ts'
import {
  ancestorIds,
  automationIdLeaf,
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

  it('ignores the marks of ş ğ ü ö ç, so ASCII typing finds Turkish text', () => {
    const cases: [string, string][] = [
      ['Giriş', 'giris'],
      ['Şifre', 'sifre'],
      ['Oturum Aç', 'oturum ac'],
      ['Değiştir', 'degistir'],
      ['Kullanıcı', 'kullanici'],
      ['ID', 'id'],
      ['Gözat ÜST', 'gozat ust'],
    ]
    for (const [text, typed] of cases) {
      assert.ok(foldText(text).includes(foldText(typed)), `${typed} -> ${text}`)
    }
    assert.equal(foldText('ŞĞÜÖÇİI şğüöçıi'), 'sguocii sguocii')
  })

  it('still finds Turkish text typed with its own letters', () => {
    assert.ok(foldText('Giriş').includes(foldText('giriş')))
    assert.ok(foldText('Kullanıcı adı').includes(foldText('KULLANICI ADI')))
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

  it('matches the nearest label, so a text box with no name is found by its caption', () => {
    const edit = { controlType: 'Edit', name: '', nearestLabel: 'Kullanıcı adı:' }
    assert.ok(elementMatches(edit, 'kullanici'))
    assert.ok(!elementMatches({ controlType: 'Edit', name: '' }, 'kullanici'))
  })

  it('matches the plain type label when given', () => {
    const label = (type: string) => (type === 'Edit' ? 'Text box' : type)
    assert.ok(elementMatches({ controlType: 'Edit' }, 'text box', label))
    assert.ok(!elementMatches({ controlType: 'Edit' }, 'text box'))
  })

  it('searches a dotted Qt AutomationId by its last part only (#204)', () => {
    const button = { controlType: 'Button', automationId: 'QApplication.loginWindow.loginButton' }
    const input = { controlType: 'Edit', automationId: 'QApplication.loginWindow.usernameInput' }
    // "login" is in the window's part of every id; only the button's own part has it.
    assert.ok(elementMatches(button, 'login'))
    assert.ok(!elementMatches(input, 'login'))
    assert.ok(!elementMatches(input, 'qapplication'))
    // A pasted id, or part of one with a dot, is matched against the whole id.
    assert.ok(elementMatches(input, 'loginWindow.username'))
    assert.ok(elementMatches(input, 'QApplication.loginWindow.usernameInput'))
  })

  it('takes the whole id when it has no dots', () => {
    assert.equal(automationIdLeaf('userName'), 'userName')
    assert.equal(automationIdLeaf('a.b.c'), 'c')
    assert.equal(automationIdLeaf(''), '')
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
