"""Bring KeePass 2 into the window state the #6 dump was taken in (#161).

The #6 dump of `keepass2` was taken with a database open and the **Add Entry** dialog on
top, set up by hand. Re-measuring the walk (#161) needs that state again and again, so it
is scripted here.

Driving KeePass's new-database wizard blind does not work: it is six dialogs deep, two of
them are message boxes that appear only sometimes, and every WinForms element goes stale
the moment a dialog is replaced (`COMError -2146233083`). So this script never follows a
fixed sequence — it looks at what is on screen, does the one thing that moves it forward,
and looks again:

    startup message box ("the last database is gone")   -> OK
    new-database notice                                 -> OK  (CommandButton_1)
    Save As                                             -> Save, keeping the default path
    Create Master Key                                   -> type the password twice, OK
    "the master password is weak"                       -> Yes
    Configure New Database                              -> OK
    emergency sheet                                     -> Skip
    main window with a database                         -> Ctrl+I

Usage (Windows only; the database is created once and reused afterwards):

    python kp_state.py entry        # database open + Add Entry dialog: the #6 state
    python kp_state.py main         # database open, main window only
    python kp_state.py start        # fresh start, nothing opened
    python kp_state.py entry --fresh    # delete the database first and build it again

It prints the window handles at the end, which is what `uia_probe.py --handle` wants.

**Known limitation (2026-10-31):** this script has not yet run the whole wizard unattended.
It reliably gets as far as the master-key dialog; after the Save As dialog closes, the file
dialog's controls stay in the main form's UIA tree for a while, and a pass can answer the
wrong dialog. If it stops making progress, confirm the dialog on screen by hand and run it
again — the state it is trying to reach is the one described above. Fixing this needs a
check that a control is still the live one before pressing it (#161, Open issues).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

EXE = r"C:\ayna-pilots\keepass2\KeePass.exe"
DB = os.path.expandvars(r"%USERPROFILE%\OneDrive\Belgeler\Database.kdbx")
PW = "ayna-demo"
STEP_TIMEOUT = 90


def windows() -> list:
    """Every visible top-level window of KeePass, by handle rather than through the UIA tree.

    KeePass's modal dialogs are owned by a child window of the main form, so a UIA-only
    search misses them from both ends (the same reason `uia_dump.find_windows` enumerates
    handles, #6).
    """
    from uia_dump import find_windows

    return find_windows("KeePass.exe", None)


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
    control = controls(window, "Button").get(name)
    if control is None:
        return False
    try:
        control.click_input()
        return True
    except Exception:
        return False


def type_password(window, repeated: bool = True) -> bool:
    """KeePass's secure text boxes ignore the value pattern, so click and type.

    The create dialog asks for the password twice, the open dialog once.
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
            box.click_input()
        except Exception:
            return False
        time.sleep(0.3)
        send_keys(PW, pause=0.03)
    time.sleep(0.3)
    return True


def advance(want_entry: bool, typed: set) -> str:
    """Do the one thing that moves the wizard forward. Returns what it did.

    Conditions are checked in priority order across *all* windows, not window by window:
    a message box sits on top of the dialog that opened it and has to be answered first,
    and which of the two the window enumeration returns first is not fixed.
    """
    from pywinauto.keyboard import send_keys

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
            return "save as" if press(window, "Save") else "stuck"
    for _info, window, found in buttons:
        if "CommandButton_1" in found:                           # new-database notice
            return "new-database notice" if press(window, "CommandButton_1") else "stuck"

    main = main_window()
    if main is None:
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

    subprocess.run([r"C:\Windows\System32\taskkill.exe", "/IM", "KeePass.exe", "/F"],
                   capture_output=True)
    time.sleep(1.5)
    if args.fresh and os.path.exists(DB):
        os.remove(DB)

    subprocess.Popen([EXE])
    time.sleep(4)

    if args.state != "start":
        reach(args.state)
    report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
