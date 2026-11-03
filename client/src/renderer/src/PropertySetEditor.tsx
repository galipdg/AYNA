import type { ElementDescriptor } from '../../shared/element.ts'
import {
  IDENTIFYING_FIELDS,
  type IdentifyingField,
  type PropertySet,
  type PropertyUse,
} from '../../shared/repository.ts'
import { controlTypeLabel, strings } from './strings.ts'

/** One identifying property of an element: its (editable) value and how AYNA uses it. */
export interface Row {
  field: IdentifyingField
  value: string
  use: PropertyUse
}

/** The element's identifying properties, in priority order, each with the use `useOf` gives. */
export function elementRows(
  element: Partial<ElementDescriptor>,
  useOf: (field: IdentifyingField) => PropertyUse,
): Row[] {
  return IDENTIFYING_FIELDS.flatMap((field) => {
    const value = element[field]
    return value === undefined ? [] : [{ field, value: String(value), use: useOf(field) }]
  })
}

/**
 * The rows of a saved object: its own values first (the user may have edited them), the
 * captured element's for the properties it does not use.
 */
export function objectRows(object: {
  primary: PropertySet
  fallback: PropertySet
  element: Partial<ElementDescriptor>
}): Row[] {
  const { primary, fallback, element } = object
  return elementRows({ ...element, ...fallback, ...primary }, (field) =>
    field in primary ? 'primary' : field in fallback ? 'fallback' : 'unused',
  )
}

/** The rows of one use as a property set, or the first problem with their values. */
export function propertySet(rows: Row[], use: PropertyUse): PropertySet | string {
  const set: Record<string, string | number> = {}
  for (const row of rows.filter((candidate) => candidate.use === use)) {
    const label = strings.spyProperties[row.field]
    if (row.field === 'siblingIndex') {
      if (!/^\d+$/.test(row.value.trim())) return strings.repoNotInteger(label)
      set[row.field] = Number(row.value.trim())
    } else {
      // Kept as typed: a value with surrounding spaces is still a real UIA value.
      if (!row.value) return strings.repoEmptyValue(label)
      set[row.field] = row.value
    }
  }
  return set as PropertySet
}

/** The problems of the rows' property sets, in the order the user fixes them. */
export function rowProblems(rows: Row[]): string[] {
  const primary = propertySet(rows, 'primary')
  const fallback = propertySet(rows, 'fallback')
  return [
    typeof primary === 'string' && primary,
    typeof primary !== 'string' && Object.keys(primary).length === 0 && strings.repoNoPrimary,
    typeof fallback === 'string' && fallback,
  ].filter((problem): problem is string => !!problem)
}

/** The summary's words: plain labels where the glossary has one, plain control types. */
export function fieldLabel(field: IdentifyingField): string {
  return field in strings.spyPlain
    ? strings.spyPlain[field as keyof typeof strings.spyPlain]
    : strings.spyProperties[field]
}

export function fieldValue(field: IdentifyingField, value: string | number | boolean): string {
  return field === 'controlType' ? controlTypeLabel(String(value)) : String(value)
}

/**
 * "How AYNA finds it": the Find by properties, how many elements of the capture they match
 * (when there is a capture) and which properties are the backup.
 */
export function FoundBy({ rows, matches }: { rows: Row[]; matches?: number }) {
  const findBy = rows.filter((row) => row.use === 'primary')
  const backup = rows.filter((row) => row.use === 'fallback')
  return (
    <div className="repo-summary">
      {findBy.length === 0 ? (
        <p className="field-error">{strings.repoNoPrimary}</p>
      ) : (
        <dl>
          {findBy.map((row) => (
            <div key={row.field}>
              <dt>{fieldLabel(row.field)}</dt>
              <dd>{fieldValue(row.field, row.value)}</dd>
            </div>
          ))}
        </dl>
      )}
      {matches !== undefined && findBy.length > 0 && (
        <p className={matches === 1 ? 'tone-success' : 'field-error'} role="status">
          {strings.repoMatches(matches)}
        </p>
      )}
      {backup.length > 0 && (
        <p className="hint">{strings.repoBackup(backup.map((row) => fieldLabel(row.field)))}</p>
      )}
    </div>
  )
}

/** One row per identifying property: its value and Find by / Backup / Don't use. */
export function PropertyTable({
  rows,
  onChange,
}: {
  rows: Row[]
  onChange: (field: IdentifyingField, update: Partial<Row>) => void
}) {
  return (
    <table className="repo-properties">
      <thead>
        <tr>
          <th scope="col">{strings.repoPropertyHeader}</th>
          <th scope="col">{strings.repoValueHeader}</th>
          <th scope="col">{strings.repoUseHeader}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => {
          const label = strings.spyProperties[row.field]
          return (
            <tr key={row.field}>
              <th scope="row" title={row.field}>
                {label}
              </th>
              <td>
                <input
                  aria-label={`${label}: ${strings.repoValueHeader}`}
                  value={row.value}
                  inputMode={row.field === 'siblingIndex' ? 'numeric' : undefined}
                  onChange={(event) => onChange(row.field, { value: event.target.value })}
                />
              </td>
              <td>
                <select
                  aria-label={`${label}: ${strings.repoUseHeader}`}
                  value={row.use}
                  onChange={(event) =>
                    onChange(row.field, { use: event.target.value as PropertyUse })
                  }
                >
                  {(['primary', 'fallback', 'unused'] as const).map((use) => (
                    <option key={use} value={use}>
                      {strings.repoUses[use]}
                    </option>
                  ))}
                </select>
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
