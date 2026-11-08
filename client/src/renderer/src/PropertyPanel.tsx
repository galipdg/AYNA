import {
  ELEMENT_FIELDS,
  formatBounds,
  formatDpi,
  type ElementDescriptor,
  type ElementField,
} from '../../shared/element.ts'
import { strings } from './strings.ts'

function formatValue(element: ElementDescriptor, field: ElementField): string | undefined {
  switch (field) {
    case 'bounds':
      return element.bounds && formatBounds(element.bounds)
    case 'dpi':
      return element.dpi === undefined ? undefined : formatDpi(element.dpi)
    case 'nearestLabelSource':
      return element.nearestLabelSource && strings.spyLabelSources[element.nearestLabelSource]
    case 'enabled':
    case 'offscreen': {
      const value = element[field]
      return value === undefined ? undefined : value ? strings.spyYes : strings.spyNo
    }
    default: {
      const value = element[field]
      return value === undefined ? undefined : String(value)
    }
  }
}

/** Every descriptor field of one element; the ones the agent did not capture say so. */
export default function PropertyPanel({
  element,
  note,
}: {
  element: ElementDescriptor
  note?: string
}) {
  return (
    <section className="spy-properties" aria-label={strings.spyPropertiesTitle}>
      <header className="panel-header">
        <h2>{strings.spyPropertiesTitle}</h2>
      </header>
      {note && <p className="message message-warning">{note}</p>}
      <dl className="facts">
        {ELEMENT_FIELDS.map((field) => {
          const value = formatValue(element, field)
          return (
            <div key={field} className="property" title={field}>
              <dt>{strings.spyProperties[field]}</dt>
              {value === undefined ? (
                <dd className="not-captured">{strings.spyNotCaptured}</dd>
              ) : (
                <dd>{value}</dd>
              )}
            </div>
          )
        })}
      </dl>
    </section>
  )
}
