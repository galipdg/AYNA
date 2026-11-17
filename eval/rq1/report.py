"""RQ1's report: the recognition rate per app and per control type, with Wilson intervals (#64).

    .venv/Scripts/python.exe eval/rq1/report.py                 # writes eval/rq1/report.md
    .venv/Scripts/python.exe eval/rq1/report.py --stdout        # prints it instead

`measure.py` (#29) does the measuring and this does the arithmetic and the writing, so the two
can be read apart: a change to what counts as recognised belongs there, a change to how the
number is presented belongs here.

**Only labelled screens enter a rate.** An unlabelled screen has the wrong denominator in both
directions — a control the walk never found is silently missing from it, and a composite
control's inner parts are silently in it — so mixing the two produces a number that means
nothing. `measure --labels` prints an app line that does exactly that mixing, and a rate taken
from it had to be retracted once (`memory-bank/people/hasan/active.md`, 2026-11-14). Every rate
here therefore carries its own coverage: how many screens of the app it rests on.

**Wilson, not the normal approximation** (RS §4.1, ref [37]). At these sample sizes the normal
interval is indefensible: 35 of 35 recognised gives `1.0 ± 0.0`, which claims certainty from 35
observations, and anything at 100 % gives a zero-width interval. Wilson gives `[90.1 %, 100 %]`
for the same data, which is what the evidence supports.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from math import sqrt
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Imported after the path insert above, which is what makes it importable.
from measure import (
    AMBIGUOUS,
    NO_PROPERTY,
    Control,
    Screen,
    counted,
    load_apps,
    pilot_ids,
    read_screens,
)

HERE = Path(__file__).resolve().parent
REPORT = HERE / "report.md"

#: NFR-27: "at least 90 % of the standard controls in the pilot apps shall be recognised by
#: multi-property identification" (RS §3.3; RQ1; SC-06).
NFR_27_TARGET = 0.90

#: 95 %, two-sided. The RS fixes the level for every proportion in the project (§4.1).
Z_95 = 1.959963984540054


@dataclass(frozen=True)
class Rate:
    """One proportion and what it rests on."""

    label: str
    recognised: int
    total: int
    #: How many screens contributed, and how many of the app's captured screens that is.
    screens: int = 0
    screens_available: int = 0

    @property
    def share(self) -> float:
        return self.recognised / self.total if self.total else 0.0

    @property
    def interval(self) -> tuple[float, float]:
        return wilson(self.recognised, self.total)

    @property
    def meets_target(self) -> bool:
        """**The lower bound**, not the point estimate.

        35 of 35 is 100 %, and its interval still reaches down to 90.1 %: the data is
        consistent with the target and does not establish a margin above it. Judging NFR-27 on
        the point estimate would turn "we saw no failures in 35 tries" into "at least 90 % of
        the pilot apps' controls are recognised", which is a far larger claim.
        """
        return self.total > 0 and self.interval[0] >= NFR_27_TARGET


def wilson(successes: int, total: int, z: float = Z_95) -> tuple[float, float]:
    """The Wilson score interval for a proportion [37].

    Zero observations give `(0.0, 1.0)` — everything is possible and nothing is known — rather
    than a division by zero or a misleading `(0, 0)`.
    """
    if total <= 0:
        return (0.0, 1.0)
    if successes < 0 or successes > total:
        raise ValueError(f"{successes} successes out of {total}")
    proportion = successes / total
    denominator = 1 + z**2 / total
    centre = proportion + z**2 / (2 * total)
    spread = z * sqrt(proportion * (1 - proportion) / total + z**2 / (4 * total**2))
    low = (centre - spread) / denominator
    high = (centre + spread) / denominator
    return (max(0.0, low), min(1.0, high))


def percent(value: float) -> str:
    return f"{value * 100:.1f}"


def interval_text(rate: Rate) -> str:
    low, high = rate.interval
    return f"[{percent(low)}, {percent(high)}]"


# ------------------------------------------------------------------------------ gathering


def labelled_screens(screens: list[Screen]) -> list[Screen]:
    return [screen for screen in screens if screen.labelled]


def controls_of(screens: list[Screen]) -> list[Control]:
    """Every control that counts, from the labelled screens only."""
    return [
        control for screen in labelled_screens(screens) for control in counted(screen)
    ]


def missing_count(screens: list[Screen]) -> int:
    """Controls a person saw that no element row carries: in the denominator, never recognised."""
    return sum(len(screen.missing) for screen in labelled_screens(screens))


def rate_of(
    label: str,
    controls: list[Control],
    *,
    missing: int = 0,
    screens: int = 0,
    available: int = 0,
) -> Rate:
    recognised = sum(1 for control in controls if control.recognised)
    return Rate(
        label=label,
        recognised=recognised,
        total=len(controls) + missing,
        screens=screens,
        screens_available=available,
    )


def per_control_type(controls: list[Control]) -> list[Rate]:
    """One rate per control type, most controls first, so the big ones are read first."""
    by_type: dict[str, list[Control]] = {}
    for control in controls:
        by_type.setdefault(control.control_type or "(none)", []).append(control)
    rates = [rate_of(name, group) for name, group in by_type.items()]
    return sorted(rates, key=lambda rate: (-rate.total, rate.label))


def unrecognised(controls: list[Control]) -> list[Control]:
    return [control for control in controls if not control.recognised]


# ------------------------------------------------------------------------------- writing


def report_lines(
    apps: dict[str, dict[str, Any]], app_ids: list[str], today: str
) -> list[str]:
    everything: list[Control] = []
    all_missing = 0
    per_app: list[Rate] = []
    sections: list[list[str]] = []

    for app_id in app_ids:
        screens = read_screens(app_id, labels=True)
        done = labelled_screens(screens)
        controls = controls_of(screens)
        missing = missing_count(screens)
        everything.extend(controls)
        all_missing += missing
        per_app.append(
            rate_of(
                apps[app_id].get("app", app_id),
                controls,
                missing=missing,
                screens=len(done),
                available=len(screens),
            )
        )
        sections.append(app_section(apps[app_id], app_id, screens))

    lines = header(today, apps, app_ids)
    lines += overall(everything, all_missing, per_app)
    lines += ["", "## Per application", ""] + app_table(per_app)
    for section in sections:
        lines += section
    lines += unrecognised_section(everything)
    lines += caveats()
    return lines


def header(
    today: str, apps: dict[str, dict[str, Any]], app_ids: list[str]
) -> list[str]:
    named = ", ".join(
        f"{apps[a].get('app', a)} ({apps[a].get('technology', '?')})" for a in app_ids
    )
    return [
        "# RQ1 — recognition rate on the pilot apps",
        "",
        f"Generated by `eval/rq1/report.py` on {today}. Measurements by `eval/rq1/measure.py`",
        "(#29); ground truth in `eval/rq1/labels/`. Applications: " + named + ".",
        "",
        "**What a rate here is.** The share of the controls a person labelled `control` on a",
        "captured screen for which the Spy's proposed property set matches exactly one element.",
        "A set that matches none or several is not recognised, and a control a person saw that",
        "the walk never produced (`missing`) is in the denominator and never recognised.",
        "",
        "Intervals are Wilson 95 % [37], as the RS fixes for every proportion (§4.1).",
        "",
    ]


def overall(controls: list[Control], missing: int, per_app: list[Rate]) -> list[str]:
    total = rate_of("All labelled screens", controls, missing=missing)
    verdict = nfr_27_verdict(total, per_app)
    return [
        "## The short answer",
        "",
        (
            f"Over every labelled screen: **{total.recognised} of {total.total} "
            f"= {percent(total.share)} %**, Wilson 95 % {interval_text(total)}."
        ),
        "",
        *verdict,
    ]


def nfr_27_verdict(total: Rate, per_app: list[Rate]) -> list[str]:
    """Whether NFR-27 is met, and — separately — whether it is *evaluated*."""
    covered = sum(rate.screens for rate in per_app)
    available = sum(rate.screens_available for rate in per_app)
    partial = covered < available

    if total.total == 0:
        return [
            "**NFR-27 cannot be evaluated**: no screen is labelled yet, so there is no",
            "denominator. Label a screen (`eval/rq1/labelling.md`) and run this again.",
        ]

    low = percent(total.interval[0])
    if total.meets_target:
        met = (
            f"**NFR-27 is met on the evidence there is**: the interval's lower bound is {low} %, "
            f"at or above the 90 % the requirement asks for."
        )
    else:
        met = (
            f"**NFR-27 is not demonstrated**: the point estimate is {percent(total.share)} % but "
            f"the interval reaches down to {low} %, so the data is also consistent with a true "
            f"rate below 90 %. More labelled controls would narrow it; a wider sample is the "
            f"remedy, not a different statistic."
        )

    scope = (
        f"**And it is evaluated on {covered} of {available} captured screens**, which is not the "
        f"same as 'the pilot apps'. A rate over {covered} screens describes those screens. Until "
        f"every captured screen is labelled, read the number as provisional in coverage as well "
        f"as in width."
        if partial
        else f"Every captured screen ({covered}) is labelled."
    )
    return [met, "", scope]


def app_table(per_app: list[Rate]) -> list[str]:
    lines = [
        "| Application | Recognised | Rate | Wilson 95 % | Labelled screens | NFR-27 |",
        "|---|---|---|---|---|---|",
    ]
    for rate in per_app:
        if rate.total == 0:
            lines.append(
                f"| {rate.label} | — | — | — | "
                f"{rate.screens} of {rate.screens_available} | not evaluated |"
            )
            continue
        lines.append(
            f"| {rate.label} | {rate.recognised} / {rate.total} | {percent(rate.share)} % | "
            f"{interval_text(rate)} | {rate.screens} of {rate.screens_available} | "
            f"{app_verdict(rate)} |"
        )
    return lines


def app_verdict(rate: Rate) -> str:
    """Never a bare "met" while screens are unlabelled.

    A one-word verdict is the thing a reader lifts out of a table and quotes, so it carries its
    own scope: "met on 1 of 4 screens" cannot be repeated as "met for KeePass 2". That is not
    pedantry — a rate of mine was quoted exactly that way and had to be retracted (#29).
    """
    if rate.total == 0:
        return "not evaluated"
    whole = rate.screens >= rate.screens_available and rate.screens_available > 0
    if rate.meets_target:
        return (
            "met"
            if whole
            else f"met on {rate.screens} of {rate.screens_available} screens"
        )
    return "not shown"


def app_section(
    app: Mapping[str, Any], app_id: str, screens: list[Screen]
) -> list[str]:
    done = labelled_screens(screens)
    name = app.get("app", app_id)
    lines = ["", f"### {name}", ""]
    if not done:
        unlabelled = ", ".join(f"`{s.screen}`" for s in screens) or "none captured"
        lines += [
            f"No labelled screen. Captured and waiting for ground truth: {unlabelled}.",
            "",
        ]
        return lines

    labelled_names = ", ".join(f"`{s.screen}`" for s in done)
    waiting = ", ".join(f"`{s.screen}`" for s in screens if not s.labelled)
    lines += [
        f"Labelled: {labelled_names}."
        + (f" Not yet labelled: {waiting}." if waiting else "")
    ]
    lines += [
        "",
        "| Control type | Recognised | Rate | Wilson 95 % |",
        "|---|---|---|---|",
    ]
    for rate in per_control_type(controls_of(screens)):
        lines.append(
            f"| {rate.label} | {rate.recognised} / {rate.total} | {percent(rate.share)} % | "
            f"{interval_text(rate)} |"
        )
    lines.append("")
    return lines


def unrecognised_section(controls: list[Control]) -> list[str]:
    failures = unrecognised(controls)
    lines = ["", "## The controls that were not recognised", ""]
    if not failures:
        return lines + [
            "None, on the screens labelled so far. That is a statement about those screens; the",
            "interval above is what says how far it generalises.",
            "",
        ]

    reasons = Counter(control.reason for control in failures)
    lines += [
        f"{len(failures)} of {len(controls)} labelled controls. By reason: "
        + ", ".join(f"**{reason}** {count}" for reason, count in reasons.most_common())
        + ".",
        "",
        "| App | Screen | Control type | Name | Reason | Proposed set | Matched |",
        "|---|---|---|---|---|---|---|",
    ]
    for control in failures:
        descriptor = control.descriptor
        # `Element` is a dataclass, not a mapping (`ayna_agent.model`). Name first, because
        # that is what a reader recognises on the screen; the AutomationId is the fallback,
        # and a control with neither is exactly the interesting kind of failure.
        shown = str(
            getattr(descriptor, "name", None)
            or getattr(descriptor, "automation_id", None)
            or ""
        )
        lines.append(
            f"| {control.app} | {control.screen} | {control.control_type} | {shown or '—'} | "
            f"{explain(control.reason)} | "
            f"{', '.join(control.primary) if control.primary else '(none)'} | "
            f"{control.match_count} |"
        )
    lines.append("")
    return lines


def explain(reason: str) -> str:
    if reason == NO_PROPERTY:
        return "no identifying property to propose"
    if reason == AMBIGUOUS:
        return "the proposed set matched more than one element"
    return reason


def caveats() -> list[str]:
    return [
        "",
        "## What this does not establish",
        "",
        "- **One labeller.** `eval/rq1/labelling.md` §2 asks for a second person to review the",
        "  ground truth, and that is still owed from #29. A rate from one labeller is",
        "  provisional, because the denominator is a judgement and nobody has checked it.",
        "- **Captured screens, not sessions.** Each rate is one snapshot of one screen in one",
        "  state. A control that is only reachable after loading a file, or only on a second",
        "  tab, is not in any denominator here.",
        "- **Nothing about playback.** Recognition is whether the Spy's proposed set matches",
        "  exactly one element in the captured tree. Whether a step then acts on it is #40's",
        "  question, and whether it keeps working across a UI change is RQ4's (#46).",
        "",
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "apps", nargs="*", help="app ids from apps.json (default: the D1 pilots)"
    )
    parser.add_argument(
        "--stdout", action="store_true", help="print the report instead of writing it"
    )
    parser.add_argument(
        "--date", default=None, help="the date in the header (default: today)"
    )
    args = parser.parse_args(argv)

    apps = load_apps()
    app_ids = args.apps or pilot_ids(apps)
    unknown = [app_id for app_id in app_ids if app_id not in apps]
    if unknown:
        print(f"error: not in apps.json: {', '.join(unknown)}", file=sys.stderr)
        return 2

    from datetime import date

    today = args.date or date.today().isoformat()
    text = "\n".join(report_lines(apps, app_ids, today)).rstrip() + "\n"
    if args.stdout:
        print(text)
        return 0
    REPORT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {REPORT.relative_to(HERE.parents[1])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
