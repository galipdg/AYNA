import { useEffect, useRef, useState, type ReactNode } from 'react'

/**
 * A top-bar button that opens a small panel under it. The panel closes on Esc, on a click
 * outside it, and when its content calls `close`.
 */
export default function Menu({
  label,
  title,
  className,
  align = 'start',
  children,
}: {
  label: ReactNode
  /** Tooltip and accessible name when the label alone is not enough. */
  title?: string
  className?: string
  align?: 'start' | 'end'
  children: (close: () => void) => ReactNode
}) {
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function outside(event: MouseEvent) {
      if (!root.current?.contains(event.target as Node)) setOpen(false)
    }
    function escape(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', outside)
    document.addEventListener('keydown', escape)
    return () => {
      document.removeEventListener('mousedown', outside)
      document.removeEventListener('keydown', escape)
    }
  }, [open])

  return (
    <div className="menu" ref={root}>
      <button
        type="button"
        className={['menu-button', className].filter(Boolean).join(' ')}
        aria-expanded={open}
        aria-haspopup="dialog"
        title={title}
        onClick={() => setOpen(!open)}
      >
        {label}
      </button>
      {open && (
        <div className={`menu-panel menu-${align}`} role="dialog" aria-label={title}>
          {children(() => setOpen(false))}
        </div>
      )}
    </div>
  )
}
