"""The UI Automation backend: the only part of recognition that needs Windows (#12, #16).

This is the `Desktop` that `ayna_agent.rpc` expects. It answers `listWindows` and `snapshot`,
turning a window handle into the document of `schemas/snapshot.schema.json`. Everything about
the document's *shape* lives in `recognition/snapshot.py` and is tested on any OS; what lives
here is the reading, and it can only be judged on a real desktop.

**Nothing is imported from pywinauto at module import.** The server runs `setup()`, every call
and `close()` on one dedicated thread (`ayna-uia`, PR #135), and COM has to be initialised on
the thread that uses it, so the import and `CoInitializeEx` happen in `setup()`.

Two things here are measurements rather than preferences, both from #161
(`eval/spikes/uia-walk-cost.md`):

- **The walk reads 12 properties per element, not the dump's 17 plus ten pattern probes.** The
  descriptor (#11) stores twelve, the schema refuses the rest, and the probes cost 23 % of a
  walk while no matching property uses them. So the measured 15.3 ms per WinForms element is an
  upper bound for this walk.
- **The budget is a deadline on a timer, not a check between elements.** Under a modal message
  box a single child enumeration blocked for **72 s** and the median element was still 1.4 ms;
  code inside a blocking cross-process call cannot look at a clock. So the walk runs on its own
  thread and `snapshot` stops waiting when the budget is gone, abandoning that thread. The
  clock is *also* checked between elements, which is what stops a merely huge window early and
  keeps an abandoned walk from running forever.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import ntpath
import sys
import threading
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any

from ayna_agent import __version__
from ayna_agent.recognition import snapshot as snap
from ayna_agent.rpc import SnapshotTimeout, UiaUnavailable, WindowNotFound

log = logging.getLogger(__name__)

#: How deep and how wide a walk may go before it gives up. These are not a second kind of
#: budget: hitting either is the same outcome as running out of time (-32002, no document). They
#: exist so that a provider reporting a cycle cannot make the walk run until the deadline.
MAX_ELEMENTS = 20_000
MAX_DEPTH = 64

#: How much longer than its budget a walk may take to notice the deadline itself.
_JOIN_GRACE_S = 0.25

#: DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2. Every coordinate the agent reports is then in
#: physical pixels (docs/agent-rpc.md), which is what the healing scorer's DIP comparison and
#: the screenshot crop rectangle (#54) both assume.
_PER_MONITOR_AWARE_V2 = -4

#: Window styles, from winuser.h. A child window is not a window a snapshot can be asked for.
_WS_CHILD = 0x4000_0000

#: DWMWA_CLOAKED: a window the compositor hides although Win32 calls it visible. Windows 10 and
#: 11 keep several per session (suspended UWP apps, the "Windows Input Experience"), and a Spy
#: picker that lists them is listing windows a tester cannot see.
_DWMWA_CLOAKED = 14


class UiaDesktop:
    """Reads the desktop through UI Automation. One instance per agent process.

    Every method runs on the server's single `ayna-uia` thread, so there is no locking here;
    the one thing that escapes it is an abandoned walk thread, which never touches state the
    next call reads.
    """

    def __init__(self, default_budget_ms: int = snap.DEFAULT_BUDGET_MS) -> None:
        self.default_budget_ms = default_budget_ms
        self._ready = False
        #: Why this host cannot read UI Automation, or None. Set by `setup()`.
        self._unavailable: str | None = None
        self._type_names: dict[int, str] = {}
        #: Walks that passed their budget and were left running. Counted for the log and for
        #: the diagnostics of the next timeout: a provider that stays stuck leaks one thread
        #: per attempt, and that is worth saying out loud rather than hiding.
        self._abandoned = 0

    # --- lifecycle, on the ayna-uia thread -----------------------------------------------

    def setup(self) -> None:
        """Make this thread able to read UI Automation.

        It deliberately does **not** raise when UI Automation cannot run here.
        `docs/agent-rpc.md` says a host without a backend answers `-32001` per call, and a
        server that refused to start instead would stop the client, the Spy and these very
        tests from running on macOS, where two of the three of us develop. The reason is
        recorded and every method raises `UiaUnavailable` with it, which is the documented
        behaviour and the more useful one: a named reason per call beats a dead process.
        """
        self._unavailable = None
        if sys.platform != "win32":
            self._stay_unavailable(
                f"UI Automation needs Windows, this is {sys.platform}"
            )
            return
        _set_dpi_awareness()
        try:
            import pythoncom
            import pywinauto  # noqa: F401  (sets sys.coinit_flags: MTA where possible)
            from pywinauto.uia_defines import IUIA
        except ImportError as exc:  # pywinauto, comtypes or pywin32 missing
            self._stay_unavailable(f"pywinauto is not usable here: {exc}")
            return
        try:
            pythoncom.CoInitializeEx(sys.coinit_flags)
            self._type_names = dict(IUIA().known_control_type_ids)
        except Exception as exc:  # noqa: BLE001 - a COM error, or no UIA on this Windows
            self._stay_unavailable(f"UI Automation did not start: {exc!r}")
            return
        self._ready = True
        log.info(
            "UI Automation ready: %d control types, default budget %d ms",
            len(self._type_names),
            self.default_budget_ms,
        )

    def _stay_unavailable(self, reason: str) -> None:
        self._ready = False
        self._unavailable = reason
        log.warning("no UI Automation on this host: %s", reason)

    def close(self) -> None:
        if not self._ready:
            return
        import pythoncom

        self._ready = False
        if self._abandoned:
            log.warning(
                "%d snapshot walk(s) were abandoned this session", self._abandoned
            )
        pythoncom.CoUninitialize()

    # --- methods the client calls --------------------------------------------------------

    def list_windows(self) -> list[dict[str, Any]]:
        """The visible top-level windows, as `listWindows` returns them (docs/agent-rpc.md).

        The handles come from Win32 `EnumWindows`, not from the UIA tree: KeePass 2's modal
        `Add Entry` dialog is owned by a child of the main form, and a UIA-only search misses
        it from both ends (#6). Everything the window manager knows is reachable by handle, so
        the enumeration starts there and only converts the matches to UIA elements.
        """
        self._require_ready()
        import win32gui
        from pywinauto.uia_element_info import UIAElementInfo

        windows: list[dict[str, Any]] = []

        def collect(handle: int, _: Any) -> bool:
            if not _is_pickable_window(handle):
                return True
            info = _quiet(lambda: UIAElementInfo(handle))
            left, top, right, bottom = win32gui.GetWindowRect(handle)
            process_id = _window_process(handle)
            windows.append(
                {
                    "handle": handle,
                    "title": _quiet(lambda: info.name) if info else None,
                    "className": _quiet(lambda: info.class_name) if info else None,
                    "processId": process_id,
                    "processName": _exe_name(process_id),
                    "bounds": [left, top, right, bottom],
                }
            )
            return True

        win32gui.EnumWindows(collect, None)
        return windows

    def snapshot(self, handle: int, timeout_ms: int | None) -> dict[str, Any]:
        """One window's whole subtree, as the snapshot schema defines it.

        Raises WindowNotFound when `handle` is not a top-level window any more, and
        SnapshotTimeout when the walk did not finish inside its budget -- then there is no
        partial document, because candidates ranked from a partial tree would give a confident
        but unfounded proposal (RS 0.6 FR-29/FR-35).
        """
        progress, started_at, duration_ms, budget_ms = self._walk_window(
            handle, timeout_ms
        )
        return snap.build(
            progress.nodes,
            window=progress.window,
            app=progress.app,
            started_at=started_at,
            duration_ms=duration_ms,
            budget_ms=budget_ms,
            read_errors=progress.read_errors,
            agent_version=__version__,
        )

    def read_tree(
        self, handle: int, timeout_ms: int | None = None
    ) -> tuple[list[dict[str, Any]], list[Any]]:
        """The window's raw nodes in pre-order and the live element behind each one.

        What `snapshot` reads, before it becomes a document: `(nodes, infos)` of equal length,
        where a node is the snake_case mapping `ayna_agent.model.describe_tree` takes. Playback
        (#26) resolves a target by deriving descriptors from `nodes` -- the *same* derivation a
        snapshot uses, so a repository object matches the values it was stored with -- and then
        acts on the element at the same index.

        Raises the same errors as `snapshot` for the same reasons, timeout included: a target
        resolved from a partial tree could be the wrong element, which is worse than no answer.
        """
        progress, _started_at, _duration_ms, _budget_ms = self._walk_window(
            handle, timeout_ms
        )
        return progress.nodes, progress.infos

    def _walk_window(
        self, handle: int, timeout_ms: int | None
    ) -> tuple[_Progress, datetime, int, int]:
        """Walk one window inside its budget, on a thread that can be abandoned.

        Shared by `snapshot` and `read_tree`, because the budget, the abandoned-thread case and
        the "no partial tree" rule are properties of reading a window, not of what the caller
        does with the result.
        """
        self._require_ready()
        budget_ms = timeout_ms or self.default_budget_ms
        if not _is_window(handle) or _is_child(handle):
            raise WindowNotFound(handle)

        progress = _Progress()
        started_at = datetime.now().astimezone()
        start = time.perf_counter()
        worker = threading.Thread(
            target=self._walk_in_thread,
            args=(handle, budget_ms, progress),
            name=f"ayna-uia-walk-{handle}",
            daemon=True,
        )
        worker.start()
        # A grace period over the budget: the walk checks the same clock between elements, so
        # without it a walk that is stopping itself would be reported as abandoned.
        worker.join(budget_ms / 1000 + _JOIN_GRACE_S)
        duration_ms = round((time.perf_counter() - start) * 1000)

        if worker.is_alive():
            # The thread is inside a cross-process call that will not come back on its own.
            # It is left running and its result discarded; the most likely cause is an
            # application that has stopped pumping messages (#161), which the message says,
            # because "the app is showing a message box" is actionable and "timeout" is not.
            self._abandoned += 1
            raise SnapshotTimeout(
                f"walk stopped after {budget_ms} ms; reached {progress.reached} element(s) "
                f"and was blocked on {progress.blocked_on}. The application is most likely "
                f"not pumping messages (a modal message box, a tracked menu or a drag)"
            )
        if progress.error is not None:
            raise progress.error
        if progress.timed_out:
            raise SnapshotTimeout(
                f"walk stopped after {duration_ms} ms of a {budget_ms} ms budget, "
                f"having reached {progress.reached} element(s); the window needs more time "
                f"than the budget allows"
            )
        return progress, started_at, duration_ms, budget_ms

    # --- the walk itself, on its own thread ----------------------------------------------

    def _walk_in_thread(self, handle: int, budget_ms: int, progress: _Progress) -> None:
        """Read the window on a thread of its own, so the deadline can be enforced.

        Both threads live in the same COM apartment (pywinauto aims for MTA), so the elements
        this thread creates are usable by the caller; it initialises COM for itself all the
        same, because a thread that never did cannot make a COM call at all.
        """
        import pythoncom

        try:
            pythoncom.CoInitializeEx(sys.coinit_flags)
        except Exception as exc:  # noqa: BLE001 - COM raises many types; all mean the same
            progress.error = UiaUnavailable(
                f"COM did not start on the walk thread: {exc!r}"
            )
            return
        try:
            self._walk(handle, budget_ms, progress)
        except Exception as exc:  # noqa: BLE001 - carried to the caller's thread verbatim
            progress.error = exc
        finally:
            pythoncom.CoUninitialize()

    def _walk(self, handle: int, budget_ms: int, progress: _Progress) -> None:
        """Read the window behind `handle`, which is the only step that needs pywinauto."""
        from pywinauto.uia_element_info import UIAElementInfo

        root = UIAElementInfo(handle)
        dpi = _window_dpi(handle)
        title = _quiet(lambda: root.name)
        progress.window = {
            "handle": handle,
            "title": title,
            "className": _quiet(lambda: root.class_name),
            "processId": _window_process(handle),
            "bounds": _bounds(root),
            "dpi": dpi,
        }
        progress.app = _app_info(_window_process(handle))
        self.walk_from(root, handle, budget_ms, progress, title=title, dpi=dpi)

    def walk_from(
        self,
        root: Any,
        root_handle: int,
        budget_ms: int,
        progress: _Progress,
        *,
        title: str | None,
        dpi: int | None,
    ) -> None:
        """Flatten the tree under `root` into `progress.nodes`, in pre-order.

        `root` is duck-typed on what `UIAElementInfo` offers -- `children()`, `handle`, `name`,
        `class_name` and `element.Current*` -- which is what lets the order, the deduplication
        and the deadline be tested with fakes on any OS (`agent/AGENTS.md`).
        """
        deadline = time.perf_counter() + budget_ms / 1000
        # Deduplicated by window handle: an owned dialog is a top-level window and usually
        # also a descendant of its owner (KeePass's `Add Entry` is a child of the main form's
        # ToolBar, #6), so without this the subtree is read twice. The first visit wins,
        # subtree included; an element without a handle is never skipped.
        seen: set[int] = {root_handle}
        stack: list[tuple[Any, int | None, int, int]] = [(root, None, 0, 0)]
        while stack:
            if time.perf_counter() > deadline or len(progress.nodes) >= MAX_ELEMENTS:
                progress.timed_out = True
                return
            info, parent, depth, index = stack.pop()
            node_id = len(progress.nodes)
            node = self._read(info, progress)
            node.update(
                {
                    "id": node_id,
                    "parent": parent,
                    "sibling_index": index,
                    "window_title": title,
                    "dpi": dpi,
                }
            )
            progress.nodes.append(node)
            progress.infos.append(info)
            progress.reached = len(progress.nodes)
            # Set from values already read, so naming the element a walk got stuck on costs
            # no extra cross-process call. Blocking happens in `children()` far more often
            # than in a property read (#161: six containers held 170 s of a 230 s walk).
            progress.blocked_on = _describe(node)
            if depth >= MAX_DEPTH:
                progress.timed_out = True
                return
            children = self._children(info, progress)
            kept = []
            for child in children:
                child_handle = _quiet(lambda node=child: node.handle)
                if child_handle:
                    if child_handle in seen:
                        continue
                    seen.add(child_handle)
                kept.append(child)
            for position, child in reversed(list(enumerate(kept))):
                stack.append((child, node_id, depth + 1, position))

    def _read(self, info: Any, progress: _Progress) -> dict[str, Any]:
        """The twelve properties the descriptor stores, each read on its own.

        pywinauto's own properties turn a COM error into None or "", which hides it, so every
        property is read separately: a failing call (an element that vanished, a provider that
        does not implement a property) costs only that value and is counted.
        """
        element = info.element

        def get(call: Callable[[], Any]) -> Any:
            try:
                return call()
            except Exception:  # noqa: BLE001 - comtypes COMError, or pywinauto on a provider
                progress.read_errors += 1
                return None

        type_id = get(lambda: element.CurrentControlType)
        labeled_by = get(lambda: element.CurrentLabeledBy)
        return {
            "control_type": self._type_names.get(type_id, type_id),
            "automation_id": get(lambda: element.CurrentAutomationId),
            "name": get(lambda: element.CurrentName),
            "class_name": get(lambda: element.CurrentClassName),
            "framework_id": get(lambda: element.CurrentFrameworkId),
            "help_text": get(lambda: element.CurrentHelpText),
            "access_key": get(lambda: element.CurrentAccessKey),
            "enabled": get(lambda: bool(element.CurrentIsEnabled)),
            "offscreen": get(lambda: bool(element.CurrentIsOffscreen)),
            "native_window_handle": get(lambda: element.CurrentNativeWindowHandle)
            or None,
            # A NULL COM pointer is falsy: most elements have no LabeledBy, and only Qt filled
            # it in the four #6 dumps. It is still the best label when it is there (#11).
            "labeled_by": get(lambda: labeled_by.CurrentName) if labeled_by else None,
            "bounds": _bounds(info),
        }

    def _children(self, info: Any, progress: _Progress) -> list[Any]:
        try:
            return info.children() or []
        except Exception:  # noqa: BLE001 - a failing provider costs this subtree, not the walk
            progress.read_errors += 1
            return []

    def _require_ready(self) -> None:
        if not self._ready:
            raise UiaUnavailable(
                self._unavailable or "the UI Automation backend has not been set up"
            )


class _Progress:
    """What a walk has done so far, readable from the thread that is waiting for it.

    Only the waiting thread reads it, and only after `join` has either returned or timed out,
    so the plain attributes are enough: the fields the timeout path reads (`reached`,
    `blocked_on`) are single assignments of immutable values.
    """

    __slots__ = (
        "app",
        "blocked_on",
        "error",
        "infos",
        "nodes",
        "reached",
        "read_errors",
        "timed_out",
        "window",
    )

    def __init__(self) -> None:
        self.nodes: list[dict[str, Any]] = []
        #: The live element behind each node, same order and length as `nodes`. A snapshot
        #: throws these away, but playback (#26, #40) has to act on the element it resolved,
        #: and re-finding it by position afterwards would be a second walk and a second
        #: chance to pick the wrong one.
        self.infos: list[Any] = []
        self.window: dict[str, Any] = {}
        self.app: dict[str, Any] = {}
        self.read_errors = 0
        self.reached = 0
        self.blocked_on = "the window itself"
        self.timed_out = False
        self.error: BaseException | None = None


# --- small Win32 helpers -------------------------------------------------------------------


def _quiet(call: Callable[[], Any]) -> Any:
    """`call()`, or None when it raises. For the reads whose failure is not worth counting."""
    try:
        return call()
    except Exception:  # noqa: BLE001 - any COM failure here means "this value is unknown"
        return None


def _describe(node: dict[str, Any]) -> str:
    """A short name for the last element a walk read, for a timeout message.

    Built from values the walk has already read, so naming the element it got stuck on costs
    no extra cross-process call.
    """
    name = (node.get("name") or "")[:40]
    which = node.get("automation_id") or node.get("class_name") or "?"
    label = f" {name!r}" if name else ""
    return f"element {node['id']} ({node.get('control_type') or '?'} {which}{label})"


def _bounds(info: Any) -> list[int] | None:
    rect = _quiet(lambda: info.element.CurrentBoundingRectangle)
    if rect is None:
        return None
    return [rect.left, rect.top, rect.right, rect.bottom]


def _set_dpi_awareness() -> None:
    """Per-monitor-v2, so every coordinate is in physical pixels.

    Already being DPI aware (an application manifest, or a second call) is success, not
    failure: the only thing that matters is that the process is not scaled by Windows.
    """
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    try:
        if user32.SetProcessDpiAwarenessContext(_PER_MONITOR_AWARE_V2):
            return
    except (AttributeError, OSError):  # needs Windows 10 1703+
        log.warning(
            "SetProcessDpiAwarenessContext is missing; coordinates may be scaled"
        )
        return
    error = ctypes.get_last_error()
    if error in (5, 87):  # ERROR_ACCESS_DENIED: already set. ERROR_INVALID_PARAMETER.
        log.info("DPI awareness was already set before the backend started")
    else:
        log.warning("could not set per-monitor-v2 DPI awareness (error %d)", error)


def _is_window(handle: int) -> bool:
    import win32gui

    return bool(_quiet(lambda: win32gui.IsWindow(handle)))


def _is_child(handle: int) -> bool:
    import win32con
    import win32gui

    style = _quiet(lambda: win32gui.GetWindowLong(handle, win32con.GWL_STYLE)) or 0
    return bool(style & _WS_CHILD)


def _is_pickable_window(handle: int) -> bool:
    """A window a person could point at: visible, not a child, with an area, not cloaked."""
    import win32gui

    if not win32gui.IsWindowVisible(handle) or _is_child(handle):
        return False
    left, top, right, bottom = win32gui.GetWindowRect(handle)
    if right - left <= 0 or bottom - top <= 0:
        # Frameworks keep hidden message-only helpers (WinForms' broadcast window, IME
        # windows) that are "visible" to Win32 but have nothing to walk (#6).
        return False
    return not _is_cloaked(handle)


def _is_cloaked(handle: int) -> bool:
    cloaked = ctypes.c_int(0)
    try:
        result = ctypes.windll.dwmapi.DwmGetWindowAttribute(
            ctypes.wintypes.HWND(handle),
            _DWMWA_CLOAKED,
            ctypes.byref(cloaked),
            ctypes.sizeof(cloaked),
        )
    except (AttributeError, OSError):  # no desktop composition
        return False
    return result == 0 and cloaked.value != 0


def _window_process(handle: int) -> int | None:
    import win32process

    found = _quiet(lambda: win32process.GetWindowThreadProcessId(handle))
    return found[1] if found else None


def _exe_name(process_id: int | None) -> str | None:
    """Exe file name without its path; None when it cannot be read (an elevated process)."""
    if process_id is None:
        return None
    from pywinauto.application import process_module

    path = _quiet(lambda: process_module(process_id))
    return ntpath.basename(path) if path else None


def _app_info(process_id: int | None) -> dict[str, Any]:
    """`{exeName, fileVersion}`. The full path is left out on purpose: it names the user (#6)."""
    if process_id is None:
        return {}
    import win32api
    from pywinauto.application import process_module

    path = _quiet(lambda: process_module(process_id))
    if not path:
        return {}
    info = _quiet(lambda: win32api.GetFileVersionInfo(path, "\\"))
    version = None
    if info:
        high, low = info["FileVersionMS"], info["FileVersionLS"]
        version = f"{high >> 16}.{high & 0xFFFF}.{low >> 16}.{low & 0xFFFF}"
    return {"exeName": ntpath.basename(path), "fileVersion": version}


def _window_dpi(handle: int) -> int | None:
    """The DPI the window renders at. One top-level window has one DPI, and a child HWND
    inherits it, so this is every element's `dpi` in the snapshot."""
    try:
        return ctypes.windll.user32.GetDpiForWindow(handle) or None
    except (AttributeError, OSError):  # needs Windows 10 1607+
        return None
