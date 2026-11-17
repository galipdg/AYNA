"""#64's report: the Wilson interval, and the claims the report is allowed to make.

The arithmetic is checked against values computed independently rather than against whatever
this implementation happens to return — a statistics function tested on its own output is a
tautology, and this one decides whether the project reports NFR-27 as met.

The rest of the file is about **what the report may say**. Two rules carry the weight:

- a rate is judged on the interval's **lower bound**, never on the point estimate;
- a verdict never appears without its coverage, because a one-word verdict is what gets quoted.

Both exist because a rate of mine was quoted out of its scope once and had to be retracted
(#29, `memory-bank/people/hasan/active.md`).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Imported after the path insert above, which is what makes them importable.
import report
from measure import Control, Screen

try:  # the descriptor type the controls carry
    from ayna_agent.model import Element
except ImportError:  # pragma: no cover - the agent is on the path in CI and locally
    Element = None


# --- the interval ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("successes", "total", "low", "high"),
    [
        # Cross-checked against the root-finding below, which solves the score equation the
        # interval is *defined* by rather than evaluating the same closed form twice.
        (35, 35, 0.901099, 1.000000),
        (4, 6, 0.299993, 0.903229),
        (0, 2, 0.000000, 0.657620),
        (39, 41, 0.838610, 0.986519),
        (1, 1, 0.206549, 1.000000),
        (50, 100, 0.403832, 0.596168),
    ],
    ids=["35-of-35", "4-of-6", "0-of-2", "39-of-41", "1-of-1", "half"],
)
def test_the_interval_matches_an_independent_computation(successes, total, low, high):
    got_low, got_high = report.wilson(successes, total)
    assert got_low == pytest.approx(low, abs=5e-6)
    assert got_high == pytest.approx(high, abs=5e-6)


def score_equation(p: float, successes: int, total: int) -> float:
    """`(p_hat - p)^2 - z^2 p(1 - p) / n`, whose two roots *are* the Wilson bounds."""
    z = report.Z_95
    return (successes / total - p) ** 2 - z * z * p * (1 - p) / total


def root_between(successes: int, total: int, lo: float, hi: float) -> float:
    for _ in range(200):
        mid = (lo + hi) / 2
        if (
            score_equation(lo, successes, total) * score_equation(mid, successes, total)
            <= 0
        ):
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


@pytest.mark.parametrize(
    ("successes", "total"),
    [(35, 35), (4, 6), (0, 2), (39, 41), (1, 1), (50, 100), (7, 13), (2, 97)],
)
def test_the_closed_form_solves_the_equation_it_claims_to(successes, total):
    """A different computation, not the same one twice.

    The closed form is an algebraic solution of the score equation; this bisects for the roots
    numerically. If a sign or a term in the formula were wrong, the two would part company —
    which is the only check worth having on a statistic that decides whether the project
    reports NFR-27 as met.
    """
    low, high = report.wilson(successes, total)
    proportion = successes / total
    if successes:
        assert low == pytest.approx(
            root_between(successes, total, 0.0, proportion), abs=1e-9
        )
    if successes != total:
        assert high == pytest.approx(
            root_between(successes, total, 1.0, proportion), abs=1e-9
        )


def test_a_perfect_score_does_not_claim_certainty():
    """The reason for Wilson rather than the normal approximation, in one assertion."""
    low, high = report.wilson(35, 35)
    assert high == 1.0
    assert low < 1.0, "a normal interval would give 1.0 +/- 0.0 and claim certainty"
    assert 0.89 < low < 0.91


def test_a_zero_score_is_not_certain_either():
    low, high = report.wilson(0, 2)
    assert low == 0.0
    assert high > 0.6, "two observations cannot rule much out"


def test_no_observations_is_everything_possible_rather_than_a_crash():
    assert report.wilson(0, 0) == (0.0, 1.0)


def test_the_interval_is_always_inside_zero_and_one():
    for total in range(1, 40):
        for successes in range(total + 1):
            low, high = report.wilson(successes, total)
            assert 0.0 <= low <= high <= 1.0, (successes, total)


def test_more_data_narrows_the_interval():
    narrow = report.wilson(90, 100)
    wide = report.wilson(9, 10)
    assert (narrow[1] - narrow[0]) < (wide[1] - wide[0])


def test_more_successes_than_trials_is_refused():
    with pytest.raises(ValueError, match="3 successes out of 2"):
        report.wilson(3, 2)


# --- what may be claimed ------------------------------------------------------------------


def rate(
    recognised: int, total: int, screens: int = 1, available: int = 1
) -> report.Rate:
    return report.Rate(
        "X", recognised, total, screens=screens, screens_available=available
    )


def test_the_target_is_judged_on_the_lower_bound_not_the_point_estimate():
    """39/41 is 95.1 %, comfortably above 90 — and its interval reaches 83.9 %."""
    assert rate(39, 41).share > report.NFR_27_TARGET
    assert not rate(39, 41).meets_target


def test_a_rate_whose_whole_interval_clears_the_target_counts_as_met():
    assert rate(35, 35).meets_target
    assert report.wilson(35, 35)[0] >= report.NFR_27_TARGET


def test_nothing_measured_meets_nothing():
    assert not rate(0, 0).meets_target


def test_a_verdict_carries_its_coverage_while_screens_are_unlabelled():
    """The word a reader lifts out of the table has to limit itself."""
    partial = report.app_verdict(rate(35, 35, screens=1, available=4))
    assert partial == "met on 1 of 4 screens"
    assert report.app_verdict(rate(35, 35, screens=4, available=4)) == "met"


def test_a_rate_that_does_not_clear_the_target_says_so_plainly():
    assert report.app_verdict(rate(4, 6)) == "not shown"


def test_an_app_with_no_labelled_screen_is_not_evaluated():
    assert report.app_verdict(rate(0, 0, screens=0, available=3)) == "not evaluated"


# --- the report over real-ish data ---------------------------------------------------------


def a_control(
    app: str, screen: str, control_type: str, matches: int, label: str = "control"
):
    return Control(
        app=app,
        screen=screen,
        snapshot_id="s1",
        element_id="e1",
        control_type=control_type,
        descriptor=Element(name="Save") if Element else None,
        primary={"automationId": "save"} if matches else {},
        match_count=matches,
        label=label,
    )


def a_screen(app: str, name: str, controls, labelled: bool = True, missing=()):
    return Screen(
        app=app,
        screen=name,
        path=Path(f"{app}-{name}.json"),
        document={"window": {"title": name}},
        controls=list(controls),
        missing=list(missing),
        labelled=labelled,
    )


def test_only_labelled_screens_contribute_to_a_rate():
    """The trap the module docstring names: mixing the two makes the number meaningless."""
    screens = [
        a_screen("x", "done", [a_control("x", "done", "Button", 1)], labelled=True),
        a_screen(
            "x",
            "raw",
            [a_control("x", "raw", "Button", 0) for _ in range(99)],
            labelled=False,
        ),
    ]
    controls = report.controls_of(screens)
    assert len(controls) == 1, "the 99 unlabelled controls stayed out"
    assert report.rate_of("x", controls).share == 1.0


def test_an_ignored_row_is_out_of_the_denominator():
    screen = a_screen(
        "x",
        "s",
        [
            a_control("x", "s", "Button", 1, label="control"),
            a_control("x", "s", "Text", 0, label="ignore"),
        ],
    )
    controls = report.controls_of([screen])
    assert [c.control_type for c in controls] == ["Button"]


def test_a_control_nobody_found_is_in_the_denominator_and_never_recognised():
    """`missing` is the whole reason labelling exists: it puts back what the walk lost."""
    screen = a_screen(
        "x", "s", [a_control("x", "s", "Button", 1)], missing=["the Help button"]
    )
    got = report.rate_of(
        "x", report.controls_of([screen]), missing=report.missing_count([screen])
    )
    assert (got.recognised, got.total) == (1, 2)
    assert got.share == 0.5


def test_control_types_are_listed_with_the_biggest_group_first():
    controls = [a_control("x", "s", "Button", 1) for _ in range(3)]
    controls += [a_control("x", "s", "TabItem", 1)]
    assert [r.label for r in report.per_control_type(controls)] == ["Button", "TabItem"]


def test_the_unrecognised_list_is_exactly_the_failures():
    controls = [
        a_control("x", "s", "Button", 1),
        a_control("x", "s", "MenuItem", 0),
        a_control("x", "s", "MenuItem", 3),
    ]
    failures = report.unrecognised(controls)
    assert [c.control_type for c in failures] == ["MenuItem", "MenuItem"]
    assert [c.match_count for c in failures] == [0, 3]


def test_a_reason_is_put_into_words_rather_than_left_as_a_code():
    assert "more than one" in report.explain(report.AMBIGUOUS)
    assert "no identifying property" in report.explain(report.NO_PROPERTY)


# --- the file that gets committed -------------------------------------------------------


def test_the_committed_report_is_what_the_generator_produces_today():
    """So `report.md` can never drift from the labels it claims to summarise.

    Regenerate with `.venv/Scripts/python.exe eval/rq1/report.py` when labels change; the date
    line is excluded, since the report is not rewritten merely because a day passed.
    """
    committed = (Path(report.__file__).parent / "report.md").read_text(encoding="utf-8")
    apps = report.load_apps()
    fresh = (
        "\n".join(report.report_lines(apps, report.pilot_ids(apps), "DATE")).rstrip()
        + "\n"
    )

    def without_date(text: str) -> list[str]:
        return [
            line for line in text.splitlines() if not line.startswith("Generated by")
        ]

    assert without_date(committed) == without_date(fresh)
