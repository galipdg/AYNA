"""A window's two rectangles, straight from Win32. No UI Automation, no RPC, no dependencies.

`frame_bounds` used to live in `recognition/uia.py`. It moved for #54: a screenshot needs
nothing from that module but these two rectangles, while importing it drags in the whole UI
Automation backend -- pywinauto, comtypes, a COM apartment -- and, until the same change
pointed `uia.py` at `ayna_agent.errors`, `websockets` as well (`memory-bank/learnings.md`,
2026-11-14). A headless capture (the CLI runner of #61, a measurement script) should pay for
none of that to crop an image, so these live here, where `ctypes` and `pywin32` are the only
things involved.

The pair is one subject because the crop reconciles them: `window_rect` is what `PrintWindow`
renders, `frame_bounds` is what a person sees, and the difference between them is the invisible
resize border.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes

#: DWMWA_EXTENDED_FRAME_BOUNDS: the rectangle the window *appears* to occupy. See
#: :func:`frame_bounds` for why `GetWindowRect` is the wrong answer.
DWMWA_EXTENDED_FRAME_BOUNDS = 9


def window_rect(handle: int) -> list[int]:
    """`GetWindowRect`: the whole window rectangle, invisible resize border included.

    This is the rectangle `PrintWindow` draws into, which is the only reason to want it: as a
    description of where the window *is*, it is wrong by the border (see :func:`frame_bounds`).
    """
    import win32gui

    return list(win32gui.GetWindowRect(handle))


def frame_bounds(handle: int) -> list[int]:
    """The rectangle the window appears to occupy, in physical pixels.

    **Not `GetWindowRect`.** Since Windows 10 a resizable window carries an *invisible* resize
    border outside its visible frame, and `GetWindowRect` includes it -- which is why a
    maximised browser reports a negative origin. Measured on one window at 150 % scaling:

        GetWindowRect              472 x 261   (8 px of nothing on the left, right and bottom)
        DWM extended frame bounds  456 x 253   <- what a person sees
        UIA BoundingRectangle      450 x 213   (38 px short at the top: no title bar)

    So the Spy's red frame around a *window* used to be drawn outside the window, which is what
    a tester notices first (#184, 2026-11-07). DWM's extended frame bounds is the only one of
    the three that means "the window as it looks": it drops the invisible border and keeps the
    title bar. UIA's rectangle stays the right answer for an *element*, and that is what a
    snapshot reports.

    Falls back to `GetWindowRect` when DWM declines, which it does for a window that is already
    gone -- a wrong-by-8-pixels rectangle beats no window in the list.
    """
    rect = ctypes.wintypes.RECT()
    status = ctypes.WinDLL("dwmapi").DwmGetWindowAttribute(
        ctypes.wintypes.HWND(handle),
        ctypes.c_uint(DWMWA_EXTENDED_FRAME_BOUNDS),
        ctypes.byref(rect),
        ctypes.sizeof(rect),
    )
    if status == 0:
        return [rect.left, rect.top, rect.right, rect.bottom]
    return window_rect(handle)
