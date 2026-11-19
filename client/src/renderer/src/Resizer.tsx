import { useRef } from 'react'
import { strings } from './strings.ts'

/**
 * A handle that changes a width: drag it, or use ← and → when it has the focus. A double click
 * brings the default back.
 */
export default function Resizer({
  className,
  label,
  width,
  initial,
  min,
  max,
  onResize,
}: {
  className: string
  label: string
  width: number
  initial: number
  min: number
  max: number
  onResize: (width: number) => void
}) {
  const start = useRef<{ x: number; width: number }>(undefined)
  const stop = () => (start.current = undefined)
  return (
    <div
      className={className}
      role="separator"
      aria-orientation="vertical"
      aria-label={label}
      aria-valuenow={width}
      aria-valuemin={min}
      aria-valuemax={max}
      title={strings.stepsResizeHint}
      tabIndex={0}
      onPointerDown={(event) => {
        event.preventDefault()
        event.currentTarget.setPointerCapture(event.pointerId)
        start.current = { x: event.clientX, width }
      }}
      onPointerMove={(event) => {
        if (start.current) onResize(start.current.width + event.clientX - start.current.x)
      }}
      onPointerUp={stop}
      onPointerCancel={stop}
      onDoubleClick={() => onResize(initial)}
      onKeyDown={(event) => {
        const step = { ArrowLeft: -16, ArrowRight: 16 }[event.key]
        if (step === undefined) return
        event.preventDefault()
        onResize(width + step)
      }}
    />
  )
}
