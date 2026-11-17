"""The UI Automation backend: the only part of recognition that needs Windows (#12, #16).

This is the `Desktop` that `ayna_agent.rpc` expects. It answers `listWindows`, `snapshot` and
`elementFromPoint`, turning a window handle into the document of
`schemas/snapshot.schema.json`. Everything about the document's *shape* lives in
`recognition/snapshot.py` and is tested on any OS; what lives here is the reading, and it can
only be judged on a real desktop.

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

`elementFromPoint` (#22) is the third measurement-shaped decision: it answers out of the
snapshot this object last took of the window under the point, rather than describing the hit
element on its own. Deriving a descriptor for one element would need its siblings, its parent
and the parent's siblings (`nearest_label` rules 2 and 3) and the whole ancestor chain
(`parent_path`) -- a property read per sibling, unbounded in a list, and an element whose
siblings were not read would come back with `nearestLabel: None`, which cannot be told apart
from "this element has no label". Answering from the snapshot returns *the same* descriptor the
client is already showing, which is what the Spy's pick hotkey needs.
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
from ayna_agent.errors import (
    BadStepDocument,
    SnapshotTimeout,
    UiaUnavailable,
    WindowNotFound,
)
from ayna_agent.model import text_value
from ayna_agent.recognition import snapshot as snap

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

#: DWMWA_EXTENDED_FRAME_BOUNDS: the rectangle the window *appears* to occupy. See
#: `_frame_bounds` for why `GetWindowRect` is the wrong answer.
_DWMWA_EXTENDED_FRAME_BOUNDS = 9


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
        #: The snapshot this object took last, kept so `element_from_point` can name the
        #: element the client is already showing (#22). One window at a time: the Spy captures
        #: a window and then picks inside it, and a new `snapshot` replaces this.
        self._last: _LastSnapshot | None = None

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
            process_id = _window_process(handle)
            windows.append(
                {
                    "handle": handle,
                    "title": _quiet(lambda: info.name) if info else None,
                    "className": _quiet(lambda: info.class_name) if info else None,
                    "processId": process_id,
                    "processName": _exe_name(process_id),
                    "bounds": _frame_bounds(handle),
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
        document = snap.build(
            progress.nodes,
            window=progress.window,
            app=progress.app,
            started_at=started_at,
            duration_ms=duration_ms,
            budget_ms=budget_ms,
            read_errors=progress.read_errors,
            agent_version=__version__,
        )
        # Kept for `element_from_point`: `document["elements"][i]` and `progress.infos[i]` are
        # the same element, because `snap.build` keeps the walk's pre-order and numbers the
        # ids by position (`test_elements_are_in_pre_order_with_ids_by_position`).
        self._last = _LastSnapshot(handle, document, progress.infos)
        return document

    def element_from_point(self, x: int, y: int) -> dict[str, Any]:
        """The element at a point, named in the snapshot the client already has (#22).

        `x` and `y` are **physical** pixels in virtual-desktop coordinates, which are signed:
        a maximised window on a scaled display starts at a negative origin. The process is
        per-monitor-v2 DPI aware (`_set_dpi_awareness`), so no conversion happens here.

        The reply has one shape for every outcome and a point is never an error -- a hotkey
        pressed over nothing should leave the Spy with one code path, not an exception:

        - `handle`: the top-level window under the point, or None when there is no window.
        - `bounds`: the hit element's rectangle, physical pixels, or None.
        - `snapshotId`: the snapshot of that window this object still holds, else None.
        - `elementId`, `element`: that element in that snapshot, else None.

        So `snapshotId` None means "nothing captured for this window yet", while a `snapshotId`
        with no `elementId` means "the window has changed since the capture" -- two different
        things the Spy can offer two different answers to.

        Raises `UiaUnavailable` only, and only when this host has no UI Automation.
        """
        self._require_ready()
        from pywinauto.uia_element_info import UIAElementInfo

        return self.answer_for_point(
            _root_window_at(x, y), _quiet(lambda: UIAElementInfo.from_point(x, y))
        )

    def answer_for_point(self, handle: int | None, info: Any) -> dict[str, Any]:
        """`element_from_point`'s reply for an already-made hit test.

        Split from it so the three outcomes a caller has to tell apart -- nothing captured,
        captured but changed, matched -- can be tested with fakes on any OS; the two calls it
        is split from (`WindowFromPoint`, `ElementFromPoint`) are the only Windows-only part.
        """
        reply: dict[str, Any] = {
            "handle": handle,
            "bounds": _bounds(info) if info is not None else None,
            "snapshotId": None,
            "elementId": None,
            "element": None,
        }
        last = self._last
        if last is None or handle is None or last.handle != handle:
            return reply
        reply["snapshotId"] = last.document.get("snapshotId")
        index = match_in_document(
            last.document,
            reply["bounds"],
            lambda position: (
                info is not None and _compares_equal(info, last.info(position))
            ),
            lambda position: (
                info is not None
                and self._same_stored_properties(
                    info, last.document["elements"][position].get("element", {})
                )
            ),
        )
        if index is None:
            return reply
        element = last.document["elements"][index]
        reply["elementId"] = element.get("id")
        reply["element"] = element.get("element")
        return reply

    def _same_stored_properties(self, info: Any, stored: dict[str, Any]) -> bool:
        """Whether three cheap properties of the hit element are the ones stored at capture.

        The last gate before `elementFromPoint` names a candidate that `CompareElements` did
        not confirm (a wrapper chain the walk and the hit test see differently). Three reads,
        all of them properties a provider answers from its own state, against the values the
        snapshot wrote: a control replaced by another one of the same size -- another tab's
        edit, a scrolled list's row -- fails here and the reply becomes "the window changed"
        instead of the wrong node (#227 review).

        Each value goes through `model.text_value`, because that is what the descriptor stored.
        """
        element = info.element
        type_id = _quiet(lambda: element.CurrentControlType)
        live = {
            "controlType": self._type_names.get(type_id, type_id),
            "name": _quiet(lambda: element.CurrentName),
            "automationId": _quiet(lambda: element.CurrentAutomationId),
        }
        return all(text_value(value) == stored.get(key) for key, value in live.items())

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

    def run_steps(
        self,
        handle: int,
        steps: dict[str, Any],
        targets: dict[str, Any],
        default_timeout_ms: int | None = None,
    ) -> list[dict[str, Any]]:
        """Play a step document against one window and return one result per step (#26).

        Lives on this class rather than in `playback/` because **every UI Automation call has
        to happen on the server's single `ayna-uia` thread**, in its COM apartment, and this
        object is what owns that thread. The rules themselves are in
        `ayna_agent.playback.runner`, which knows nothing about UIA; this method is only the
        place where the window reading and the step playing meet.

        Raises `UiaUnavailable` when there is no backend here, `WindowNotFound` for a handle
        that is not a top-level window, and `SnapshotTimeout` when a window cannot be read
        inside its budget -- the same three as `snapshot`, because reading the window is how a
        target is resolved -- plus `BadStepDocument` for a document that cannot be read at all.
        A step that simply fails comes back as a `failed` result instead.
        """
        from ayna_agent.playback.runner import DEFAULT_TIMEOUT_MS, StepDocumentError
        from ayna_agent.playback.runner import run_steps as play

        self._require_ready()
        try:
            results = play(
                steps,
                targets,
                lambda: self.read_tree(handle),
                default_timeout_ms=(
                    DEFAULT_TIMEOUT_MS
                    if default_timeout_ms is None
                    else default_timeout_ms
                ),
            )
        except StepDocumentError as exc:
            # The server owns the error vocabulary and imports nothing from a backend, so the
            # translation happens here rather than in `rpc.py`.
            raise BadStepDocument(str(exc)) from exc
        return [result.to_json() for result in results]

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


class _LastSnapshot:
    """One window's finished snapshot and the live element behind each of its elements.

    `document["elements"][i]` and `infos[i]` are the same element. Holding the COM pointers is
    what lets `element_from_point` ask UI Automation whether two references are the same
    element; nothing else here keeps them alive, and they stop being usable when the
    application exits, which only makes the comparison fail and the lookup answer None.
    """

    __slots__ = ("document", "handle", "infos")

    def __init__(self, handle: int, document: dict[str, Any], infos: list[Any]) -> None:
        self.handle = handle
        self.document = document
        self.infos = infos

    def info(self, index: int) -> Any:
        """The live element at `index`, or None when the walk kept none for it."""
        return self.infos[index] if 0 <= index < len(self.infos) else None


def match_in_document(
    document: dict[str, Any],
    bounds: list[int] | None,
    same_element: Callable[[int], bool],
    same_properties: Callable[[int], bool],
) -> int | None:
    """The index in `document["elements"]` of the element at `bounds`, or None.

    Pure, so the rule can be tested on any OS: the two callbacks are the only things that need
    UI Automation.

    The rule: elements whose stored bounds equal `bounds` are the candidates, and **every**
    candidate, even a single one, is put to `same_element` -- identity, not geometry, decides.
    Bounds alone would be enough only while a window keeps the same elements inside the same
    rectangles, and the changes that break that are ordinary: a tab switched, a list scrolled,
    a wizard page replaced. Each of them leaves a rectangle in place and the element behind it
    different, and answering out of a stale capture would make the Spy select the wrong node
    silently -- worse than saying "the window changed, capture again" (#227 review).

    When no candidate compares equal, the **last in pre-order** still wins, but only if
    `same_properties` holds for it: same-bounds candidates are usually a wrapper chain (a Pane
    holding one Button, both at the button's rectangle), pre-order puts a child after its
    parent, and the deepest is what a hit test returns -- while the raw view the hit test
    answers from and the control view the walk reads can disagree about *which* reference is
    that element. So the fallback keeps the wrapper case and still refuses a candidate whose
    cheap properties are not the hit element's.
    """
    if bounds is None:
        return None
    candidates = [
        index
        for index, element in enumerate(document.get("elements", []))
        if element.get("element", {}).get("bounds") == bounds
    ]
    for index in candidates:
        if same_element(index):
            return index
    if not candidates:
        return None
    deepest = candidates[-1]
    return deepest if same_properties(deepest) else None


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


#: The five `DPI_AWARENESS_CONTEXT` pseudo-handles, by name, for saying what the process got.
_AWARENESS_CONTEXTS: dict[str, int] = {
    "unaware": -1,
    "system-aware": -2,
    "per-monitor-v1": -3,
    "per-monitor-v2": _PER_MONITOR_AWARE_V2,
    "unaware-gdi-scaled": -5,
}


def dpi_awareness() -> str:
    """What this process's DPI awareness actually is, by name.

    `GetAwarenessFromDpiAwarenessContext` cannot answer this: the `DPI_AWARENESS` enum has no
    value of its own for per-monitor-v2, so v1 and v2 both read as `PER_MONITOR_AWARE`. The
    contexts have to be compared instead, which is what `AreDpiAwarenessContextsEqual` is for.
    """
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    try:
        current = user32.GetThreadDpiAwarenessContext
        equal = user32.AreDpiAwarenessContextsEqual
    except (AttributeError, OSError):  # needs Windows 10 1607+
        return "unknown"
    current.restype = ctypes.c_void_p
    equal.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    equal.restype = ctypes.wintypes.BOOL
    handle = current()
    for name, context in _AWARENESS_CONTEXTS.items():
        if equal(ctypes.c_void_p(handle), ctypes.c_void_p(context)):
            return name
    return "unknown"


def _set_dpi_awareness() -> None:
    """Per-monitor-v2, so every coordinate is in physical pixels.

    `docs/agent-rpc.md` and `schemas/snapshot.schema.json` both promise bounds "as UI
    Automation reports them to a **per-monitor-v2** DPI aware agent", so this is a contract,
    not a preference, and the function says out loud when it cannot keep it.

    **Measured 2026-11-07, which is why this is written out:** `DPI_AWARENESS_CONTEXT` is a
    pointer-sized handle, and ctypes' default conversion of a negative Python int truncates it
    to 32 bits, so the call failed with `ERROR_INVALID_PARAMETER` (87) on 64-bit Windows. The
    old code treated 87 like 5 ("already set") and logged success, while pywinauto's import --
    the next statement in `setup()` -- quietly set the process to **per-monitor-v1**. The agent
    had therefore never been v2 on any machine. Hence the explicit `argtypes`, and hence 87 is
    now a warning rather than a shrug.
    """
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    try:
        set_context = user32.SetProcessDpiAwarenessContext
    except (AttributeError, OSError):  # needs Windows 10 1703+
        log.warning(
            "SetProcessDpiAwarenessContext is missing; coordinates may be scaled"
        )
        return
    set_context.argtypes = [ctypes.c_void_p]
    set_context.restype = ctypes.wintypes.BOOL
    ctypes.set_last_error(0)
    if set_context(ctypes.c_void_p(_PER_MONITOR_AWARE_V2)):
        return
    error = ctypes.get_last_error()
    got = dpi_awareness()
    if error == 5:  # ERROR_ACCESS_DENIED: awareness can only be set once per process.
        # An application manifest or an earlier import got there first. Fine if it chose v2,
        # worth saying if it did not, because the bounds contract is what suffers.
        if got == "per-monitor-v2":
            log.info(
                "DPI awareness was already per-monitor-v2 before the backend started"
            )
        else:
            log.warning(
                "DPI awareness was already set to %s before the backend started and cannot "
                "be changed; bounds are unscaled but the per-monitor-v2 behaviour "
                "docs/agent-rpc.md describes is not in force",
                got,
            )
    else:
        log.warning(
            "could not set per-monitor-v2 DPI awareness (error %d); this process is %s",
            error,
            got,
        )


def _frame_bounds(handle: int) -> list[int]:
    """The rectangle the window appears to occupy, in physical pixels.

    **Not `GetWindowRect`.** Since Windows 10 a resizable window carries an *invisible* resize
    border outside its visible frame, and `GetWindowRect` includes it -- which is why a
    maximised browser reports a negative origin. Measured on this window at 150 % scaling:

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
        ctypes.c_uint(_DWMWA_EXTENDED_FRAME_BOUNDS),
        ctypes.byref(rect),
        ctypes.sizeof(rect),
    )
    if status == 0:
        return [rect.left, rect.top, rect.right, rect.bottom]
    import win32gui

    return list(win32gui.GetWindowRect(handle))


def _is_window(handle: int) -> bool:
    import win32gui

    return bool(_quiet(lambda: win32gui.IsWindow(handle)))


def _is_child(handle: int) -> bool:
    import win32con
    import win32gui

    style = _quiet(lambda: win32gui.GetWindowLong(handle, win32con.GWL_STYLE)) or 0
    return bool(style & _WS_CHILD)


def _root_window_at(x: int, y: int) -> int | None:
    """The top-level window at a point, or None when there is no window there (#22).

    `WindowFromPoint` answers with the deepest *window* (HWND), which in a Qt or WPF
    application is the top-level window itself and in WinForms or Win32 is often a child
    control, so `GetAncestor(GA_ROOT)` finishes the job. Deliberately not a walk up the UIA
    parents: the handle has to be the same kind `list_windows` reports, because the client
    compares it with the window it has selected, and that list comes from `EnumWindows`.
    """
    import win32con
    import win32gui

    handle = _quiet(lambda: win32gui.WindowFromPoint((x, y)))
    if not handle:
        return None
    # pywin32 rather than ctypes on purpose: an HWND is pointer-sized and ctypes' default
    # `c_int` return type truncates it. That is the #201 bug, and it is not worth repeating.
    root = _quiet(lambda: win32gui.GetAncestor(handle, win32con.GA_ROOT))
    return int(root) if root else int(handle)


def _compares_equal(one: Any, other: Any) -> bool:
    """Whether two element references are the same element, per UI Automation.

    pywinauto's `UIAElementInfo.__eq__` is `IUIAutomation::CompareElements`. A reference to an
    element that has gone makes it raise, and "it is gone" answers the question well enough.
    """
    if other is None:
        return False
    return bool(_quiet(lambda: one == other))


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
