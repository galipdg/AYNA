import type { Bounds, WindowInfo } from './api.ts'

/**
 * One UI element as the agent captured it: `$defs.element` of `schemas/element.schema.json`
 * (version 0.1, ADR 2026-10-31-element-descriptor-v0). A key is absent when the element has
 * no value for it; strings are never empty.
 */
export interface ElementDescriptor {
  automationId?: string
  name?: string
  controlType?: string
  className?: string
  frameworkId?: string
  bounds?: Bounds
  /** DPI of the element's window; 96 = 100 % scaling. */
  dpi?: number
  parentPath?: string
  siblingIndex?: number
  nearestLabel?: string
  nearestLabelSource?: 'labeledBy' | 'geometric' | 'parentRow'
  windowTitle?: string
  enabled?: boolean
  offscreen?: boolean
  helpText?: string
  accessKey?: string
  nativeWindowHandle?: number
}

export type ElementField = keyof ElementDescriptor

/** Every descriptor field, in the order the property panel shows them. */
export const ELEMENT_FIELDS = [
  'name',
  'automationId',
  'controlType',
  'className',
  'frameworkId',
  'nearestLabel',
  'nearestLabelSource',
  'windowTitle',
  'parentPath',
  'siblingIndex',
  'bounds',
  'dpi',
  'enabled',
  'offscreen',
  'helpText',
  'accessKey',
  'nativeWindowHandle',
] as const satisfies readonly ElementField[]

// Fails to compile when a descriptor field is missing from ELEMENT_FIELDS.
const allFieldsListed: Exclude<ElementField, (typeof ELEMENT_FIELDS)[number]> extends never
  ? true
  : never = true
void allFieldsListed

/**
 * What the window list already says about a top-level window, as a descriptor: its UIA
 * Name is its title. Until the agent captures trees (#12) this is all the Spy can show.
 */
export function windowDescriptor(win: WindowInfo): ElementDescriptor {
  const element: ElementDescriptor = { bounds: win.bounds }
  if (win.title.trim()) {
    element.name = win.title
    element.windowTitle = win.title
  }
  if (win.className.trim()) element.className = win.className
  if (win.handle >= 1) element.nativeWindowHandle = win.handle
  return element
}

/** Size and scale are added because testers compare those, not raw edges or DPI values. */
export function formatBounds([left, top, right, bottom]: Bounds): string {
  return `${left}, ${top}, ${right}, ${bottom} (${right - left} × ${bottom - top})`
}

export function formatDpi(dpi: number): string {
  return `${dpi} (${Math.round((dpi / 96) * 100)} %)`
}
