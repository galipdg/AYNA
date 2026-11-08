import type { ReactNode } from 'react'

/** Title, one line of help and the page's actions, above the work area. */
export default function Page({
  title,
  help,
  actions,
  children,
}: {
  title: string
  help?: string
  actions?: ReactNode
  children: ReactNode
}) {
  return (
    <section className="page" aria-label={title}>
      <header className="page-header">
        <div>
          <h1>{title}</h1>
          {help && <p className="hint">{help}</p>}
        </div>
        {actions && <div className="actions">{actions}</div>}
      </header>
      <div className="page-body">{children}</div>
    </section>
  )
}
