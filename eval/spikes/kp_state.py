r"""Bring KeePass 2 into the window state the #6 dump was taken in (#161).

The #6 dump of `keepass2` was taken with a database open and the **Add Entry** dialog on
top, set up by hand. Re-measuring the walk (#161) needs that state again and again, so it
is scripted here.

Driving KeePass's new-database wizard blind does not work: it is six dialogs deep, two of
them are message boxes that appear only sometimes, and every WinForms element goes stale
the moment a dialog is replaced (`COMError -2146233083`). So this script never follows a
fixed sequence — it looks at what is on screen, does the one thing that moves it forward,
and looks again:

    startup message box ("the last database is gone")   -> OK      (Win32)
    new-database notice                                 -> OK      (CommandButton_1)
    Save As                                             -> type the demo path, Save
    Create Master Key                                   -> focus each box, type, OK
    "the master password is weak"                       -> Yes     (Win32)
    Configure New Database                              -> OK
    emergency sheet                                     -> Skip
    main window with a database                         -> Ctrl+S, Ctrl+I

A plain message box (`#32770`) is answered with Win32 messages rather than through UIA: it
blocks the provider while it is open, so UIA cannot see it (`message_boxes`).

Usage (Windows only; the database is created once and reused afterwards):

    python kp_state.py entry        # database open + Add Entry dialog: the #6 state
    python kp_state.py main         # database open, main window only
    python kp_state.py start        # fresh start, nothing opened
    python kp_state.py entry --fresh    # delete the database first and build it again

The database is `C:\ayna-pilots\ayna-demo.kdbx` and `--fresh` deletes that file only; the
script also kills only the KeePass started from `C:\ayna-pilots\keepass2\`, never another
copy that happens to be running.

It prints the window handles at the end, which is what `uia_probe.py --handle` wants.

**How long it takes (measured 2026-11-01):** from an existing database the Add Entry state
is reached in about 16 s. A cold `--fresh` run, which has to build the database, took about
six minutes — nearly all of it inside one UIA call that blocks right after the
weak-password box, because KeePass stops pumping messages there (this is the effect #161
measured: `eval/spikes/uia-walk-cost.md`). That is why `STEP_TIMEOUT` is a budget for the
whole sequence. If a run does stop making progress, confirm the dialog on screen by hand
and run it again — the state it is trying to reach is the one described above.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

PILOT_ROOT = r"C:\ayna-pilots"
EXE = PILOT_ROOT + r"\keepass2\KeePass.exe"
EXE_NAME = "KeePass.exe"
# A demo database inside the pilot folder, never KeePass's own default
# `Documents\Database.kdbx`: that folder is OneDrive-synced on this machine and may hold a
# real vault, and `--fresh` deletes whatever this points at (#170 review).
DB = PILOT_ROOT + r"\ayna-demo.kdbx"
PW = "ayna-demo"
# For the whole sequence, not for one step: eight dialogs at 1.5 s per pass is the cheap
# part, and a single pass can be held for minutes by the very thing #161 measured — right
# after the weak-password box KeePass stops pumping and one UIA call blocks. Measured
# 2026-11-01: 16 s from an existing database, about six minutes for a cold `--fresh` run,
# which failed at 240 s for exactly this reason.
STEP_TIMEOUT = 420
POWERSHELL = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
TASKKILL = r"C:\Windows\System32\taskkill.exe"


def pids_from_output(text: str) -> list[int]:
    """The process ids in PowerShell's output: one per line, anything else ignored."""
    return [int(line.strip()) for line in text.splitlines() if line.strip().isdigit()]


def is_pilot_path(path: str) -> bool:
    """True only for a path inside `PILOT_ROOT`.

    `--fresh` deletes a file, so it may never point at a place where a person keeps a
    database of their own.
    """
    root = os.path.normcase(os.path.abspath(PILOT_ROOT))
    target = os.path.normcase(os.path.abspath(path))
    return target.startswith(root + os.sep)


def pilot_pids() -> list[int]:
    """Running KeePass processes started from `EXE`, found by image path, not by exe name.

    `taskkill /IM KeePass.exe /F` would also kill a KeePass the person at the machine is
    using (#170 review), so the pilot copy is identified by where it runs from.
    """
    query = (f"Get-CimInstance Win32_Process -Filter \"Name='{EXE_NAME}'\" | "
             f"Where-Object {{ $_.ExecutablePath -eq '{EXE}' }} | "
             "Select-Object -ExpandProperty ProcessId")
    done = subprocess.run([POWERSHELL, "-NoProfile", "-NonInteractive", "-Command", query],
                          capture_output=True, text=True)
    return pids_from_output(done.stdout)


def kill_pilot() -> list[int]:
    """Force-kill the pilot KeePass only, and report which ids were killed."""
    pids = pilot_pids()
    for pid in pids:
        subprocess.run([TASKKILL, "/PID", str(pid), "/F"], capture_output=True)
    return pids


MESSAGE_BOX_CLASS = "#32770"
BM_CLICK = 0x00F5


def message_boxes() -> list[tuple[int, str, dict[str, int]]]:
    """The pilot's visible message boxes, found with Win32 only: handle, text, buttons.

    While a modal message box is open KeePass stops pumping messages, and then UIA calls
    against the process block for minutes — #161 measured a single `FindAll` blocking for
    72 s and a whole walk at 230 s. So the one window that has to be answered first is
    exactly the one UIA cannot reach, which is what used to make this script stall at the
    weak-password box. Win32 enumeration never touches the UIA provider.

    Classic message boxes only, the ones whose text is a `Static` child. KeePass's
    new-database notice is a *task dialog* — a `DirectUIHWND` child, command links, and an
    OK button that does nothing — and it is UIA-readable, so it is left to the
    `CommandButton_1` branch of `advance`; pressing its OK here made the script loop.
    """
    import win32gui
    import win32process

    pids = set(pilot_pids())
    boxes: list[tuple[int, str, dict[str, int]]] = []

    def collect(handle: int, _: object) -> bool:
        if not win32gui.IsWindowVisible(handle):
            return True
        if win32gui.GetClassName(handle) != MESSAGE_BOX_CLASS:
            return True
        if win32process.GetWindowThreadProcessId(handle)[1] not in pids:
            return True
        texts: list[str] = []
        buttons: dict[str, int] = {}
        task_dialog = False

        def child(control: int, _unused: object) -> bool:
            nonlocal task_dialog
            label = win32gui.GetWindowText(control)
            class_name = win32gui.GetClassName(control)
            if class_name == "Button":
                buttons[label.replace("&", "")] = control
            elif class_name == "Static" and label:
                texts.append(label)
            elif class_name == "DirectUIHWND":
                task_dialog = True
            return True

        win32gui.EnumChildWindows(handle, child, None)
        if not task_dialog:
            boxes.append((handle, " ".join(texts), buttons))
        return True

    win32gui.EnumWindows(collect, None)
    return boxes


def press_win32(buttons: dict[str, int], *labels: str) -> str | None:
    """Press the first of `labels` the box offers, by posting `BM_CLICK` to that button.

    Posted, not sent: the reply is not needed and the dialog's own message loop runs it.
    """
    import win32gui

    for label in labels:
        control = buttons.get(label)
        if control is not None:
            win32gui.PostMessage(control, BM_CLICK, 0, 0)
            return label
    return None


def windows() -> list:
    """Every visible top-level window of KeePass, by handle rather than through the UIA tree.

    KeePass's modal dialogs are owned by a child window of the main form, so a UIA-only
    search misses them from both ends (the same reason `uia_tree_dump.find_windows` enumerates
    handles, #6).
    """
    from uia_tree_dump import find_windows

    try:
        return find_windows("KeePass.exe", None)
    except Exception:
        # A window closed between the Win32 enumeration and `ElementFromHandle`
        # (`UIA_E_ELEMENTNOTAVAILABLE`), which is normal while a wizard replaces its
        # dialogs. The caller treats an empty list as "nothing to do yet" and looks again.
        return []


def connect(handle: int):
    from pywinauto.application import Application

    return Application(backend="uia").connect(handle=handle).window(handle=handle)


def controls(window, control_type: str) -> dict:
    """Controls of one type, reachable by name *and* by automation id.

    KeePass's dialogs identify some buttons only by name ("Yes", "Skip") and others only
    usefully by id (the new-database notice's OK is `CommandButton_1`), so both are keys.
    """
    found = {}
    try:
        for c in window.descendants(control_type=control_type):
            try:
                info = c.element_info
                keys = (info.name, info.automation_id)
            except Exception:
                continue
            for key in keys:
                if key and key not in found:
                    found[key] = c
    except Exception:
        pass
    return found


def alive(window) -> bool:
    """Whether a window is still on screen, asked over Win32 rather than UIA.

    Used after a failed `invoke()`: pressing a button that closes its own dialog makes the
    call raise *after* it has worked, and re-finding the button then fails for the right
    reason. Win32 answers this even while the provider is blocked.
    """
    import win32gui

    try:
        return bool(win32gui.IsWindow(window.handle) and win32gui.IsWindowVisible(window.handle))
    except Exception:
        return False


def press(window, name: str) -> bool:
    """Re-find the button by name or id and press it.

    Never press a control that was looked up earlier in the same pass: opening or closing
    any dialog invalidates every element handle in the window (`COMError -2146233083`), so
    a control found a second ago may already be stale.
    """
    control = controls(window, "Button").get(name)
    if control is None:
        return False
    try:
        control.invoke()
        return True
    except Exception:
        pass
    if not alive(window):
        return True      # the press landed and closed the dialog, then invoke() complained
    control = controls(window, "Button").get(name)
    if control is None:
        return False
    try:
        control.click_input()
        return True
    except Exception:
        return False


def type_password(window, repeated: bool = True) -> bool:
    """KeePass's secure text boxes ignore the value pattern, so focus them and type.

    The create dialog asks for the password twice, the open dialog once.

    **Focus, not a click.** A `click_input()` on these boxes leaves them unfocused — the
    keystrokes go nowhere and KeePass then complains about an *empty* master password, which
    is what made this script stall at the master-key dialog (#170, measured 2026-11-01:
    the character counter stayed at "0 ch." after a click and read "9 ch." after
    `set_focus()`). The click stays only as a fallback.
    """
    from pywinauto.keyboard import send_keys

    edits = {}
    try:
        for c in window.descendants(control_type="Edit"):
            edits[c.element_info.automation_id] = c
    except Exception:
        return False
    first, repeat = edits.get("m_tbPassword"), edits.get("m_tbRepeatPassword")
    if first is None or (repeated and repeat is None):
        return False
    for box in ((first, repeat) if repeated else (first,)):
        try:
            box.set_focus()
        except Exception:
            try:
                box.click_input()
            except Exception:
                return False
        time.sleep(0.3)
        send_keys("^a")
        send_keys(PW, pause=0.03)
    time.sleep(0.3)
    return True


def save_as(window) -> bool:
    r"""Replace the file dialog's default name with `DB`, then press Save.

    The dialog opens on KeePass's default `Documents\Database.kdbx`. Accepting it would put
    the demo database in a synced folder among files that are not ours, and `--fresh`
    deletes whatever `DB` points at, so the path is written in full.
    """
    from pywinauto.keyboard import send_keys

    box = controls(window, "Edit").get("File name:")
    if box is None:
        return False
    try:
        box.set_focus()
    except Exception:
        return False
    time.sleep(0.3)
    send_keys("^a")
    send_keys(DB, pause=0.02, with_spaces=True)
    time.sleep(0.3)
    try:
        typed = box.get_value() or ""      # the box's own text, not its label
    except Exception:
        typed = ""
    if typed and typed.strip().lower() != DB.lower():
        return False                       # the path did not land, and pressing Save now
    return press(window, "Save")           # would write to KeePass's default location


def advance(want_entry: bool, typed: set) -> str:
    """Do the one thing that moves the wizard forward. Returns what it did.

    Conditions are checked in priority order across *all* windows, not window by window:
    a message box sits on top of the dialog that opened it and has to be answered first,
    and which of the two the window enumeration returns first is not fixed.
    """
    from pywinauto.keyboard import send_keys

    # Before UIA is touched at all: a box that is blocking the provider would make every
    # call below wait for it (see `message_boxes`). A file dialog is also a `#32770` window
    # but offers neither button, so it falls through to the UIA branches.
    for _handle, _text, buttons in message_boxes():
        pressed = press_win32(buttons, "Yes", "OK")
        if pressed:
            return f"message box ({pressed})"

    seen = [(info, connect(info.handle)) for info in windows()]
    buttons = [(info, window, controls(window, "Button")) for info, window in seen]

    for _info, window, found in buttons:                         # emergency sheet
        if "Skip" in found and "Print" in found:
            return "skip emergency sheet" if press(window, "Skip") else "stuck"
    for _info, window, found in buttons:                         # weak-password warning
        if "Yes" in found and "No" in found:
            return "confirm weak password" if press(window, "Yes") else "stuck"
    for info, window, found in buttons:                          # any other message box
        if info.class_name == "#32770" and "OK" in found and "CommandButton_1" not in found:
            return "message box" if press(window, "OK") else "stuck"

    # Later stages of the wizard win over earlier ones: a file dialog's controls linger in
    # the main form's tree after it closes, so "there is a File name box" is not proof that
    # the Save As dialog is still the thing to answer.
    for info, window, _found in buttons:
        if "Configure New Database" in (info.name or ""):
            return "database settings" if press(window, "OK") else "stuck"
    for info, window, _found in buttons:
        title = info.name or ""
        if "Master Key" in title or info.automation_id == "KeyCreationForm":
            if info.handle not in typed:
                if not type_password(window):
                    return "stuck"
                typed.add(info.handle)
            return "master key set" if press(window, "OK") else "stuck"
        if "Open Database" in title:
            if info.handle not in typed:
                if not type_password(window, repeated=False):
                    return "stuck"
                typed.add(info.handle)
            return "database unlocked" if press(window, "OK") else "stuck"
    for _info, window, found in buttons:
        if "File name:" in controls(window, "Edit") and "Save" in found:
            return "save as" if save_as(window) else "stuck"
    for _info, window, found in buttons:
        if "CommandButton_1" in found:                           # new-database notice
            return "new-database notice" if press(window, "CommandButton_1") else "stuck"

    main = main_window()
    if main is None:
        return "waiting"
    if len(seen) > 1:
        # A dialog of an earlier stage is still up and none of the branches above could
        # answer it this pass. Waiting is the only safe answer: sending Ctrl+N to the main
        # window here starts the wizard a second time and the script loops (#170).
        return "waiting"
    title = main[1]
    window = connect(main[0])
    try:
        window.set_focus()
    except Exception:
        return "waiting"
    time.sleep(0.6)
    if ".kdbx" not in title:
        send_keys("^n")
        return "new database"
    if "*" in title:
        send_keys("^s")                                          # write the file once
        return "save database"
    if want_entry:
        send_keys("^i")
        return "add entry"
    return "done"


def main_window() -> tuple[int, str] | None:
    for info in windows():
        if info.automation_id == "MainForm":
            return info.handle, (info.name or "")
    return None


def entry_dialog() -> int | None:
    for info in windows():
        if info.automation_id == "PwEntryForm":
            return info.handle
    return None


def reach(state: str) -> None:
    started = time.time()
    last = ""
    typed: set = set()
    while time.time() - started < STEP_TIMEOUT:
        if state == "entry" and entry_dialog() is not None:
            return
        main = main_window()
        if state == "main" and main and ".kdbx" in main[1] and "*" not in main[1]:
            return
        step = advance(want_entry=(state == "entry"), typed=typed)
        if step != last:
            print(f"  {step}", flush=True)
            last = step
        time.sleep(1.5)
    raise SystemExit(f"could not reach state {state!r} within {STEP_TIMEOUT} s")


def report() -> None:
    print("\nwindows (use these with uia_probe.py --handle):")
    for info in windows():
        print(f"  handle={info.handle} {info.name!r} id={info.automation_id!r}")
    print("database file:", DB, "exists:", os.path.exists(DB))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("state", choices=["start", "main", "entry"])
    parser.add_argument("--fresh", action="store_true",
                        help="delete the database and build it again")
    args = parser.parse_args(argv)

    if sys.platform != "win32":
        print("kp_state.py drives a Windows application.", file=sys.stderr)
        return 2
    if not os.path.exists(EXE):
        print(f"KeePass 2 not found at {EXE}", file=sys.stderr)
        return 2

    killed = kill_pilot()
    if killed:
        print("killed pilot KeePass:", ", ".join(str(pid) for pid in killed))
        time.sleep(1.5)
    if args.fresh:
        if not is_pilot_path(DB):
            print(f"refusing to delete {DB}: it is outside {PILOT_ROOT}", file=sys.stderr)
            return 2
        if os.path.exists(DB):
            os.remove(DB)

    subprocess.Popen([EXE])
    time.sleep(4)

    if args.state != "start":
        reach(args.state)
    report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
