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
  /** What is on screen now and until when; undefined while hidden. */
  private shown: { bounds: Bounds; until: number } | undefined

  show(bounds: Bounds, forMs: number = SHOW_MS): void {
    const window = this.ensureWindow()
    window.setBounds(frameRect(bounds, toDip, BORDER))
    window.showInactive()
    clearTimeout(this.hideTimer)
    this.shown = { bounds, until: Date.now() + forMs }
    this.hideTimer = setTimeout(() => this.hide(), forMs)
  }

  hide(): void {
    clearTimeout(this.hideTimer)
    this.shown = undefined
    if (this.window && !this.window.isDestroyed()) this.window.hide()
  }

  /**
   * Hides the frame for a moment (a hit test must not find it) and returns a function that puts
   * it back for the time it had left, unless something else was shown or hidden in between.
   */
  suspend(): () => void {
    const before = this.shown
    this.hide()
    if (!before) return () => {}
    return () => {
      const left = before.until - Date.now()
      if (this.shown === undefined && left > 0) this.show(before.bounds, left)
    }
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
