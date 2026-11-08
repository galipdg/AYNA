import type { ReactElement } from 'react'

// A handful of 16 px line icons drawn with currentColor, so they follow the theme.
// Inline SVG: no icon font or image is loaded (closed network, docs/ui/style-guide.md §6).
const paths = {
  spy: (
    <>
      <circle cx="8" cy="8" r="5" />
      <path d="M8 1v3M8 12v3M1 8h3M12 8h3" />
    </>
  ),
  repository: (
    <>
      <path d="M2 4.5 8 2l6 2.5L8 7z" />
      <path d="M2 8l6 2.5L14 8M2 11.5 8 14l6-2.5" />
    </>
  ),
  tests: <path d="M5 4h9M5 8h9M5 12h9M2 4h.5M2 8h.5M2 12h.5" />,
  runs: <path d="M4.5 2.5v11l9-5.5z" />,
  repairs: (
    <path d="M10.5 2.5a3 3 0 0 0-3.4 4L2.5 11.1a1.3 1.3 0 0 0 1.9 1.9L9 8.4a3 3 0 0 0 4-3.4l-1.9 1.9-1.9-.4-.4-1.9z" />
  ),
  changes: <path d="M2.5 5.5h10l-2.5-2.5M13.5 10.5h-10L6 13" />,
  users: (
    <>
      <circle cx="6" cy="5.5" r="2.5" />
      <path d="M1.5 13.5c.5-2.5 2.3-4 4.5-4s4 1.5 4.5 4M10.5 3.2a2.5 2.5 0 0 1 0 4.6M12 9.8c1.3.6 2.2 1.9 2.5 3.7" />
    </>
  ),
  settings: (
    <>
      <circle cx="8" cy="8" r="2.2" />
      <path d="M8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.4 3.4l1.4 1.4M11.2 11.2l1.4 1.4M3.4 12.6l1.4-1.4M11.2 4.8l1.4-1.4" />
    </>
  ),
  chevron: <path d="M4.5 6.5 8 10l3.5-3.5" />,
  check: <path d="M3 8.5 6.5 12 13 4.5" />,
  cross: <path d="M4 4l8 8M12 4l-8 8" />,
  warning: <path d="M8 2 1.5 13.5h13zM8 6.5v3.5M8 11.8v.2" />,
  info: (
    <>
      <circle cx="8" cy="8" r="6" />
      <path d="M8 7v4.5M8 4.8v.2" />
    </>
  ),
} satisfies Record<string, ReactElement>

export type IconName = keyof typeof paths

export default function Icon({ name }: { name: IconName }) {
  return (
    <svg
      className="icon"
      viewBox="0 0 16 16"
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {paths[name]}
    </svg>
  )
}
