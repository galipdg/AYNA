"""Put the sample app's objects into an AYNA server's object repository (Windows only, #55).

The reference scenarios (#55, #62) and RQ2 (#69) are built **in the editor**, which needs the
repository to hold every object a step targets. Adding about 90 objects with the Object Spy
by hand is slow and easy to get wrong, so this does what the Spy's "Add to repository" does
(`client/src/main/repository.ts`): capture the window with the agent's own UI Automation
reader, import that snapshot into the version, then create the object from one of its
elements.

    .venv/Scripts/python.exe eval/apps/sample/load_repository.py --server http://127.0.0.1:8081 \
        --user admin --password ...            # or set AYNA_PASSWORD
    .venv/Scripts/python.exe eval/apps/sample/load_repository.py --dry-run    # no server

The objects come from `eval/nl/objects/sample.json` (#36), plus the three settings **tab
items** of `nl_objects.TAB_ITEMS`, which share the tab bar's AutomationId. Each is located in
a capture by its AutomationId and ControlType (and a tab item by its Name), and stored with
the properties the Spy would suggest for it: the AutomationId, plus what is needed to make
the match unique in that window; the rest, up to `controlType`, becomes the fallback.

It is safe to run again: objects whose name is already in the repository are skipped. The
app is created when missing (technology `PySide6`) and so is the version (`1.0`).

The walk opens every tab, wizard page and dialog, so it launches the app five times (about
half a minute). It needs the repo-root `.venv` with the agent installed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
# The agent's own UIA reader, not a copy, as `eval/rq1/measure.py` does it.
AGENT = HERE.parents[2] / "agent"
if str(AGENT) not in sys.path:
    sys.path.append(str(AGENT))

from nl_objects import OUTPUT, TAB_ITEMS

SETTLE = 0.7

#: The identifying properties a fallback may take, in the Spy's priority order
#: (`IDENTIFYING_FIELDS` up to `controlType` in `client/src/shared/repository.ts`).
FALLBACK_FIELDS = ("name", "nearestLabel", "className", "parentPath", "controlType")


# --- what to create ------------------------------------------------------------------------


def wanted_objects(objects: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Logical name -> the properties that locate it in a capture, tab items included.

    These only *find* the element; what the object is stored with is `suggest_primary`'s.
    """
    wanted = {
        name: {"automationId": obj["automationId"], "controlType": obj["controlType"]}
        for name, obj in objects.items()
    }
    for name, label in TAB_ITEMS.items():
        wanted[name] = {
            "automationId": "QApplication.settings.tabs.qt_tabwidget_tabbar",
            "controlType": "TabItem",
            "name": label,
        }
    return wanted


def matches(element: dict[str, Any], primary: dict[str, str]) -> bool:
    return all(element.get(field) == value for field, value in primary.items())


def find_element(
    snapshot: dict[str, Any], primary: dict[str, str]
) -> dict[str, Any] | None:
    """The only node of the snapshot that the primary set finds, or None (none, or several)."""
    found = [node for node in snapshot["elements"] if matches(node["element"], primary)]
    return found[0] if len(found) == 1 else None


def suggest_primary(
    element: dict[str, Any], elements: list[dict[str, Any]]
) -> dict[str, Any]:
    """The Spy's suggestion (`suggestUses` in `client/src/shared/repository.ts`): the
    AutomationId first, then each property that narrows the matches while more than one is
    left. Qt gives a grid's headers and cells the grid's AutomationId, and the three tab items
    the tab bar's, so those end up with a Name or a ControlType too."""
    primary: dict[str, Any] = {}
    count = len(elements)
    for field in ("automationId", *FALLBACK_FIELDS):
        value = element.get(field)
        if value in (None, ""):
            continue
        narrowed = sum(
            matches(node["element"], {**primary, field: value}) for node in elements
        )
        if not primary or (count > 1 and narrowed < count):
            primary[field] = value
            count = narrowed
    return primary


def fallback_for(element: dict[str, Any], primary: dict[str, Any]) -> dict[str, Any]:
    return {
        field: element[field]
        for field in FALLBACK_FIELDS
        if field not in primary and element.get(field) not in (None, "")
    }


def plan(
    wanted: dict[str, dict[str, str]], snapshots: list[dict[str, Any]]
) -> tuple[list[tuple[str, dict[str, Any], dict[str, Any]]], list[str]]:
    """(name, snapshot, node) for every object found once in some snapshot; names not found."""
    found, missing = [], []
    for name, primary in wanted.items():
        for snapshot in snapshots:
            node = find_element(snapshot, primary)
            if node is not None:
                found.append((name, snapshot, node))
                break
        else:
            missing.append(name)
    return found, missing


# --- capturing every place an object can be ------------------------------------------------


def capture_all(desktop) -> list[dict[str, Any]]:
    """Snapshots of every screen, settings tab, wizard page and dialog of app 1.0."""
    import uia_check

    def shot(spec) -> dict[str, Any]:
        return desktop.snapshot(spec.wrapper_object().handle, None)

    def dialog(owner, name: str):
        found = owner.child_window(
            auto_id=f"QApplication.{name}", control_type="Window"
        )
        found.wait("exists", timeout=10)
        return found

    def control(window, logical: str, control_type: str):
        return window.child_window(
            auto_id=f"QApplication.{logical}", control_type=control_type
        )

    def walk(screen: str, window) -> list[dict[str, Any]]:
        shots = [shot(window)]
        if screen == "detail":
            control(window, "detail.nameInput", "Edit").set_edit_text("x")
            control(window, "detail.backButton", "Button").click_input()
            shots.append(shot(dialog(window, "discardDialog")))
        elif screen == "settings":
            for tab in window.descendants(control_type="TabItem")[1:]:
                tab.select()
                time.sleep(SETTLE)
                shots.append(shot(window))
        elif screen == "wizard":
            control(window, "wizard.nameInput", "Edit").set_edit_text("Ayşe Çelik")
            for _ in range(2):
                control(window, "wizard.nextButton", "Button").invoke()
                time.sleep(SETTLE)
                shots.append(shot(window))
            control(window, "wizard.confirmCheck", "CheckBox").toggle()
            control(window, "wizard.finishButton", "Button").click_input()
            shots.append(shot(dialog(window, "confirmDialog")))
        return shots

    snapshots: list[dict[str, Any]] = []
    for screen in ("login", "main", "detail", "settings", "wizard"):
        proc = uia_check.launch_app(screen)
        try:
            snapshots += walk(screen, uia_check.find_window(screen))
        finally:
            uia_check.kill_process_tree(proc)
    return snapshots


# --- the server ----------------------------------------------------------------------------


class Server:
    def __init__(self, base_url: str, token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def call(self, method: str, path: str, body: Any = None) -> tuple[int, Any]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(self.base_url + path, data=data, method=method)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if self.token:
            request.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(request, timeout=60) as answer:
                status, raw = answer.status, answer.read()
        except urllib.error.HTTPError as error:
            status, raw = error.code, error.read()
        return status, json.loads(raw) if raw else None

    def expect(
        self, ok: tuple[int, ...], method: str, path: str, body: Any = None
    ) -> Any:
        status, answer = self.call(method, path, body)
        if status not in ok:
            raise SystemExit(f"{method} {path} -> HTTP {status}: {answer}")
        return answer

    def login(self, user: str, password: str) -> None:
        answer = self.expect(
            (200,), "POST", "/api/auth/login", {"username": user, "password": password}
        )
        self.token = answer["token"]

    def app_and_version(self, app_name: str, version: str) -> tuple[str, str]:
        apps = self.expect((200,), "GET", "/api/apps")
        app = next((a for a in apps if a["name"] == app_name), None)
        if app is None:
            app = self.expect(
                (200, 201), "POST", "/api/apps", {"name": app_name, "technology": "PySide6"}
            )
            print(f"created app {app_name!r}")
        versions = self.expect((200,), "GET", f"/api/apps/{app['id']}/versions")
        found = next((v for v in versions if v["version"] == version), None)
        if found is None:
            found = self.expect(
                (200, 201),
                "POST",
                f"/api/apps/{app['id']}/versions",
                {"version": version},
            )
            print(f"created version {version!r}")
        return app["id"], found["id"]


def load(server: Server, app_id: str, version_id: str, found) -> int:
    existing = {
        o["name"]
        for o in server.expect((200,), "GET", f"/api/apps/{app_id}/repo-objects")
    }
    imported: set[str] = set()
    created = 0
    for name, snapshot, node in found:
        if name in existing:
            continue
        if snapshot["snapshotId"] not in imported:
            server.expect(
                (200, 201),
                "POST",
                f"/api/apps/{app_id}/versions/{version_id}/snapshots",
                snapshot,
            )
            imported.add(snapshot["snapshotId"])
        primary = suggest_primary(node["element"], snapshot["elements"])
        server.expect(
            (201,),
            "POST",
            f"/api/apps/{app_id}/repo-objects",
            {
                "name": name,
                "snapshotId": snapshot["snapshotId"],
                "snapshotElementId": node["id"],
                "primary": primary,
                "fallback": fallback_for(node["element"], primary),
            },
        )
        created += 1
    print(
        f"{created} created, {len(existing & {n for n, _, _ in found})} already there"
    )
    return created


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--server", default=os.environ.get("AYNA_SERVER_URL", "http://127.0.0.1:8080")
    )
    parser.add_argument("--user", default=os.environ.get("AYNA_USER", "admin"))
    parser.add_argument("--password", default=os.environ.get("AYNA_PASSWORD"))
    parser.add_argument(
        "--app", default="AYNA Örnek Uygulama", help="application name on the server"
    )
    parser.add_argument("--version", default="1.0")
    parser.add_argument(
        "--dry-run", action="store_true", help="capture and plan, send nothing"
    )
    args = parser.parse_args(argv)

    from ayna_agent.recognition.uia import UiaDesktop

    objects = json.loads(OUTPUT.read_text(encoding="utf-8"))["objects"]
    desktop = UiaDesktop()
    desktop.setup()
    try:
        snapshots = capture_all(desktop)
    finally:
        desktop.close()
    found, missing = plan(wanted_objects(objects), snapshots)
    print(
        f"{len(snapshots)} snapshots, {len(found)} objects found once, {len(missing)} not"
    )
    for name in missing:
        print(f"  not found exactly once: {name}")
    if args.dry_run:
        return 1 if missing else 0
    if not args.password:
        parser.error("--password (or AYNA_PASSWORD) is needed unless --dry-run")

    server = Server(args.server)
    server.login(args.user, args.password)
    app_id, version_id = server.app_and_version(args.app, args.version)
    load(server, app_id, version_id, found)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
