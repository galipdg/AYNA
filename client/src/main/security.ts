// Security policy for every renderer. Kept free of Electron imports so the Vite
// config (CSP meta tag) and plain `node --test` can use it.

/**
 * Content-Security-Policy for the renderer. Nothing outside the app itself is
 * allowed: no remote scripts, styles, fonts, images or connections.
 *
 * `dev` allows the inline scripts and styles that the Vite dev server injects
 * (React Fast Refresh, CSS hot reload). It still allows no remote origin.
 */
export function contentSecurityPolicy({ dev = false }: { dev?: boolean } = {}): string {
  const inline = dev ? " 'unsafe-inline'" : ''
  return [
    "default-src 'none'",
    `script-src 'self'${inline}`,
    `style-src 'self'${inline}`,
    "img-src 'self' data:",
    "font-src 'self'",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'none'",
  ].join('; ')
}

/**
 * Whether the renderer may load `url` at all. Only bundled files, inline data and
 * DevTools are allowed; in development also the local Vite dev server
 * (e.g. `http://localhost:5173`).
 */
export function isAllowedRequest(url: string, devServerUrl?: string): boolean {
  let parsed: URL
  try {
    parsed = new URL(url)
  } catch {
    return false
  }
  if (['file:', 'data:', 'devtools:'].includes(parsed.protocol)) return true
  if (!devServerUrl) return false
  const dev = new URL(devServerUrl)
  const sameHost = parsed.host === dev.host
  return sameHost && ['http:', 'ws:'].includes(parsed.protocol)
}

/**
 * Whether a renderer may navigate to `url`. Only the app's own entry page is
 * allowed; links to anything else are blocked.
 */
export function isAllowedNavigation(url: string, entryUrl: string): boolean {
  try {
    const target = new URL(url)
    const entry = new URL(entryUrl)
    return target.origin === entry.origin && target.pathname === entry.pathname
  } catch {
    return false
  }
}

/**
 * Whether an IPC call comes from the app's own page. Every `ipcMain.handle` checks it, so
 * a frame that is not the entry page (should one ever load) cannot use the bridge.
 */
export function isTrustedSender(frameUrl: string | undefined, entryUrl: string): boolean {
  return frameUrl !== undefined && isAllowedNavigation(frameUrl, entryUrl)
}

/** webPreferences for every AYNA window; `preload` is the preload script's absolute path. */
export function secureWebPreferences(preload: string) {
  return {
    preload,
    contextIsolation: true,
    nodeIntegration: false,
    sandbox: true,
    webSecurity: true,
    allowRunningInsecureContent: false,
    webviewTag: false,
    spellcheck: false,
  }
}

/**
 * webPreferences for the run report window (#68): a server-rendered page that needs no script
 * and no bridge, so it gets neither. The report also carries its own CSP (#59).
 */
export function reportWebPreferences() {
  return {
    contextIsolation: true,
    nodeIntegration: false,
    sandbox: true,
    javascript: false,
    webSecurity: true,
    allowRunningInsecureContent: false,
    webviewTag: false,
    spellcheck: false,
  }
}
