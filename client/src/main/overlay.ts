import { BrowserWindow, screen } from 'electron'
import type { Bounds } from '../shared/api.ts'
import { frameRect, type Rect } from './spy.ts'

const BORDER = 3
const SHOW_MS = 3_000

// A static page without scripts; data: URLs pass the session's request filter.
const PAGE =
  'data:text/html;charset=utf-8,' +
  encodeURIComponent(
    '<!doctype html><meta charset="utf-8"><style>html,body{margin:0;height:100%;' +
      'overflow:hidden;background:transparent}body{box-sizing:border-box;' +
      `border:${BORDER}px solid #e53935}</style>`,
  )

/**
 * The agent reports physical pixels; Electron places windows in DIPs. Only Windows has
 * `screenToDipRect` (it picks the scale of the display the rectangle is on); elsewhere there
 * is no UI Automation backend, so the bounds are used as they are.
 */
function toDip(rect: Rect): Rect {
  return process.platform === 'win32' ? screen.screenToDipRect(null, rect) : rect
}

/** A red frame drawn above every window, click-through and never focused. */
export class Highlighter {
  private window: BrowserWindow | undefined
  private hideTimer: NodeJS.Timeout | undefined

  show(bounds: Bounds): void {
    const window = this.ensureWindow()
    window.setBounds(frameRect(bounds, toDip, BORDER))
    window.showInactive()
    clearTimeout(this.hideTimer)
    this.hideTimer = setTimeout(() => this.hide(), SHOW_MS)
  }

  hide(): void {
    clearTimeout(this.hideTimer)
    if (this.window && !this.window.isDestroyed()) this.window.hide()
  }

  /** Call when the main window closes, so this hidden window does not keep the app alive. */
  destroy(): void {
    clearTimeout(this.hideTimer)
    if (this.window && !this.window.isDestroyed()) this.window.destroy()
    this.window = undefined
  }

  private ensureWindow(): BrowserWindow {
    if (this.window && !this.window.isDestroyed()) return this.window
    const window = new BrowserWindow({
      show: false,
      frame: false,
      transparent: true,
      backgroundColor: '#00000000',
      hasShadow: false,
      resizable: false,
      movable: false,
      minimizable: false,
      maximizable: false,
      fullscreenable: false,
      focusable: false,
      skipTaskbar: true,
      alwaysOnTop: true,
      webPreferences: {
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: true,
        javascript: false,
        spellcheck: false,
      },
    })
    window.setAlwaysOnTop(true, 'screen-saver')
    window.setIgnoreMouseEvents(true)
    window.loadURL(PAGE)
    this.window = window
    return window
  }
}
