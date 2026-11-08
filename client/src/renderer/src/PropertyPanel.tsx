import type { ReactNode } from 'react'
import {
  ELEMENT_FIELDS,
  formatBounds,
  formatDpi,
  type ElementDescriptor,
  type ElementField,
} from '../../shared/element.ts'
import { controlTypeLabel, strings } from './strings.ts'

/** A descriptor field as the tester reads it in Advanced (UIA names, exact values). */
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

const yesNo = (value: boolean | undefined) =>
  value === undefined ? undefined : value ? strings.spyYes : strings.spyNo

/** Label → value pairs; missing values are left out. */
function Group({ title, items }: { title: string; items: [string, ReactNode | undefined][] }) {
  const shown = items.filter(([, value]) => value !== undefined)
  if (shown.length === 0) return null
  return (
    <section className="prop-group">
      <h3>{title}</h3>
      <dl className="facts">
        {shown.map(([label, value]) => (
          <div key={label} className="property">
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

/**
 * One element in plain-language groups (how AYNA finds it, where it is, its state); every
 * descriptor field, with its UI Automation name, is under Advanced (FR-02).
 */
export default function PropertyPanel({
  element,
  note,
  advancedOpen,
  onAdvancedToggle,
}: {
  element: ElementDescriptor
  note?: string
  /** Kept by the Spy, so Advanced stays open or closed from one element to the next. */
  advancedOpen: boolean
  onAdvancedToggle: (open: boolean) => void
}) {
  const { name, controlType, nearestLabel, windowTitle, bounds, enabled, offscreen } = element
  const [left, top, right, bottom] = bounds ?? []
  const plain = strings.spyPlain
  return (
    <section className="spy-properties" aria-label={strings.spyPropertiesTitle}>
      {note && <p className="message message-warning">{note}</p>}
      <Group
        title={strings.spyGroups.found}
        items={[
          [plain.name, name],
          [plain.controlType, controlType && controlTypeLabel(controlType)],
          [plain.nearestLabel, nearestLabel],
          [plain.windowTitle, windowTitle],
        ]}
      />
      <Group
        title={strings.spyGroups.where}
        items={[
          [plain.position, bounds && strings.spyPosition(left!, top!)],
          [plain.size, bounds && strings.spySize(right! - left!, bottom! - top!)],
        ]}
      />
      <Group
        title={strings.spyGroups.state}
        items={[
          [plain.enabled, yesNo(enabled)],
          [plain.visible, yesNo(offscreen === undefined ? undefined : !offscreen)],
        ]}
      />
      <details
        className="advanced"
        open={advancedOpen}
        onToggle={(event) => onAdvancedToggle(event.currentTarget.open)}
      >
        <summary>
          {strings.spyAdvanced} <span className="hint">{strings.spyAdvancedSummary}</span>
        </summary>
        <dl className="facts">
          {ELEMENT_FIELDS.map((field) => {
            const value = formatValue(element, field)
            return (
              <div key={field} className="property" title={field}>
                <dt>{strings.spyProperties[field]}</dt>
                {value === undefined ? (
                  <dd className="not-captured">{strings.spyNotCaptured}</dd>
                ) : (
                  <dd className="mono">{value}</dd>
                )}
              </div>
            )
          })}
        </dl>
      </details>
    </section>
  )
}
