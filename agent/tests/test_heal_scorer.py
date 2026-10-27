"""Hand-built cases for the self-healing scorer (#49)."""

import random
from fractions import Fraction

import pytest

from ayna_agent.heal.scorer import (
    PROPERTIES,
    SIMILO_WEIGHTS,
    area_similarity,
    levenshtein,
    location_similarity,
    normalize_text,
    rank,
    score,
    shape_similarity,
    text_similarity,
    word_similarity,
)

# A login window of the trial app as the last passing snapshot saw it (v1).
USERNAME = {
    "automationId": "QApplication.loginWindow.usernameInput",
    "name": "Kullanıcı adı",
    "controlType": "Edit",
    "className": "QLineEdit",
    "bounds": (120, 80, 320, 104),
    "parentPath": "Window:loginWindow/Group:credentials",
    "siblingIndex": 1,
    "nearestLabel": "Kullanıcı adı:",
    "windowTitle": "Giriş",
}
PASSWORD = {
    "automationId": "QApplication.loginWindow.passwordInput",
    "name": "Şifre",
    "controlType": "Edit",
    "className": "QLineEdit",
    "bounds": (120, 120, 320, 144),
    "parentPath": "Window:loginWindow/Group:credentials",
    "siblingIndex": 3,
    "nearestLabel": "Şifre:",
    "windowTitle": "Giriş",
}
LOGIN_BUTTON = {
    "automationId": "QApplication.loginWindow.loginButton",
    "name": "Giriş yap",
    "controlType": "Button",
    "className": "QPushButton",
    "bounds": (220, 170, 320, 200),
    "parentPath": "Window:loginWindow",
    "siblingIndex": 2,
    "windowTitle": "Giriş",
}


def candidate(element_id, element, **changes):
    """Copy ``element`` as a candidate with ``id``; a change to None deletes the key."""
    result = {**element, "id": element_id, **changes}
    return {key: value for key, value in result.items() if value is not None}


def ranked_ids(entries):
    return [entry.id for entry in entries]


def expected_score(target, cand):
    """Independent recomputation of S = sum(w * sim) / sum(w) from the similarities."""
    sims = score(target, cand).similarities
    total = sum(SIMILO_WEIGHTS[p] for p in sims)
    return sum(SIMILO_WEIGHTS[p] * s for p, s in sims.items()) / total


# --- scenarios ----------------------------------------------------------------------


def test_identical_element_scores_one():
    result = score(USERNAME, USERNAME)

    assert result.score == 1
    assert list(result.contributions) == list(PROPERTIES)
    assert all(sim == 1 for sim in result.similarities.values())


def test_unrelated_element_scores_low():
    menu_item = {
        "automationId": "QApplication.mainWindow.menuBar.fileMenu",
        "name": "Dosya",
        "controlType": "MenuItem",
        "className": "QMenu",
        "bounds": (0, 0, 48, 22),
        "parentPath": "Window:mainWindow/MenuBar",
        "siblingIndex": 0,
        "nearestLabel": "Düzen Görünüm",
        "windowTitle": "AYNA Demo",
    }

    result = score(USERNAME, menu_item)

    assert result.score < Fraction(3, 10)
    assert result.similarities["controlType"] == 0
    assert result.similarities["location"] == 0


def test_renamed_automation_id_still_ranks_first():
    candidates = [
        candidate(
            "e1", USERNAME, automationId="QApplication.loginWindow.userNameField"
        ),
        candidate("e2", PASSWORD),
        candidate("e3", LOGIN_BUTTON),
    ]

    best = rank(USERNAME, candidates)[0]

    assert best.id == "e1"
    assert 0 < best.result.similarities["automationId"] < 1


def test_qt_ancestor_rename_keeps_most_of_automation_id():
    # Qt's dotted AutomationId changes when an ancestor is renamed (learnings 2026-10-25).
    renamed = candidate(
        "e1", USERNAME, automationId="QApplication.signInWindow.usernameInput"
    )

    sim = score(USERNAME, renamed).similarities["automationId"]

    # "login" -> "signin" is 3 edits; the longer id has 39 characters.
    assert sim == Fraction(36, 39)


def test_moved_control_ranks_above_the_new_occupant_of_its_place():
    moved = candidate("e1", USERNAME, bounds=(120, 380, 320, 404), siblingIndex=4)
    newcomer = candidate(
        "e2",
        USERNAME,
        automationId="QApplication.loginWindow.emailInput",
        name="E-posta",
        nearestLabel="E-posta:",
    )

    ranking = rank(USERNAME, [newcomer, moved])

    assert ranked_ids(ranking) == ["e1", "e2"]
    assert ranking[0].result.similarities["location"] == 0
    assert ranking[1].result.similarities["location"] == 1


def test_changed_label_gives_partial_word_credit():
    relabelled = candidate("e1", USERNAME, nearestLabel="Kullanıcı adınız:")

    ranking = rank(USERNAME, [candidate("e2", PASSWORD), relabelled])

    assert ranking[0].id == "e1"
    assert ranking[0].result.similarities["nearestLabel"] == Fraction(1, 2)


def test_two_identical_siblings_are_told_apart_by_position():
    delete_button = {
        "name": "Sil",
        "controlType": "Button",
        "className": "QPushButton",
        "parentPath": "Window:users/Table:userTable",
        "windowTitle": "Kullanıcılar",
    }
    target = {**delete_button, "siblingIndex": 1, "bounds": (400, 140, 460, 164)}
    row_1 = candidate(
        "row-1", delete_button, siblingIndex=0, bounds=(400, 100, 460, 124)
    )
    row_2 = candidate(
        "row-2", delete_button, siblingIndex=1, bounds=(400, 140, 460, 164)
    )

    ranking = rank(target, [row_1, row_2])

    assert ranked_ids(ranking) == ["row-2", "row-1"]
    assert ranking[0].result.score == 1
    assert ranking[1].result.similarities["location"] == Fraction(60, 100)


def test_exact_tie_is_broken_by_candidate_id():
    twins = [candidate("e-b", PASSWORD), candidate("e-a", PASSWORD)]

    ranking = rank(USERNAME, twins)

    assert ranked_ids(ranking) == ["e-a", "e-b"]
    assert ranking[0].result == ranking[1].result


def test_empty_candidate_list_gives_empty_ranking():
    assert rank(USERNAME, []) == []


def test_missing_properties_are_skipped_not_scored_zero():
    target = candidate("t", USERNAME, nearestLabel=None)
    sparse = candidate("e1", USERNAME, name=None, className="   ")

    result = score(target, sparse)

    assert set(result.contributions) == set(PROPERTIES) - {
        "nearestLabel",
        "name",
        "className",
    }
    assert result.score == 1


def test_missing_candidate_value_is_not_penalised():
    # Known v0 limitation of the rule above: a candidate without a name or label is not
    # marked down for them, so it can outrank the same element with a different name.
    nameless = candidate("e1", PASSWORD, name=None, nearestLabel=None)
    named = candidate("e2", PASSWORD)

    assert ranked_ids(rank(USERNAME, [named, nameless])) == ["e1", "e2"]


def test_nothing_comparable_scores_zero():
    result = score({}, USERNAME)

    assert result.score == 0
    assert result.contributions == {}
    assert result.similarities == {}


def test_empty_bounds_skip_location_area_and_shape():
    offscreen = candidate("e1", USERNAME, bounds=(0, 0, 0, 0))

    result = score(USERNAME, offscreen)

    assert {"location", "area", "shape"}.isdisjoint(result.contributions)
    assert result.score == 1


def test_turkish_case_and_diacritics():
    assert normalize_text("  GİRİŞ  YAP ") == "giriş yap"
    assert normalize_text("KULLANICI ADI") == normalize_text("Kullanıcı adı")
    assert normalize_text("ŞİFRE") == normalize_text("şifre")
    # Decomposed "s" + combining cedilla equals the precomposed "ş".
    assert normalize_text("şifre") == normalize_text("şifre")

    upper = candidate(
        "e1", USERNAME, name="KULLANICI ADI", nearestLabel="KULLANICI ADI:"
    )
    assert score(USERNAME, upper).score == 1

    # Other diacritics stay significant: one substitution in five characters.
    no_cedilla = candidate("e2", PASSWORD, name="Sifre")
    assert score(PASSWORD, no_cedilla).similarities["name"] == Fraction(4, 5)


def test_hand_checked_score_and_contributions():
    # name: "ok" vs "ok!" is one insertion in three characters -> 2/3.
    # weights 1.5 each, total 4.5: 1.5/4.5 + 1.5/4.5 + 1.5*(2/3)/4.5 = 1/3 + 1/3 + 2/9.
    target = {"automationId": "okButton", "controlType": "Button", "name": "OK"}
    cand = {"automationId": "okButton", "controlType": "button", "name": "Ok!"}

    result = score(target, cand)

    assert result.score == Fraction(8, 9)
    assert result.contributions == {
        "automationId": Fraction(1, 3),
        "name": Fraction(2, 9),
        "controlType": Fraction(1, 3),
    }


def test_float_bounds_are_rounded_to_pixels():
    fractional = candidate("e1", USERNAME, bounds=(120.4, 79.6, 320.0, 104.2))

    assert score(USERNAME, fractional).score == 1


# --- similarity functions -----------------------------------------------------------


@pytest.mark.parametrize(
    ("a", "b", "distance"),
    [("kitten", "sitting", 3), ("flaw", "lawn", 2), ("", "abc", 3), ("abc", "abc", 0)],
)
def test_levenshtein(a, b, distance):
    assert levenshtein(a, b) == distance
    assert levenshtein(b, a) == distance


def test_text_similarity_is_normalised_by_the_longer_string():
    assert text_similarity("kitten", "sitting") == Fraction(4, 7)


def test_word_similarity_counts_shared_words():
    assert word_similarity("ok cancel", "cancel help ok") == Fraction(2, 3)
    assert word_similarity(":", ":") == 1
    assert word_similarity(":", "ok") == 0


@pytest.mark.parametrize(
    ("dx", "dy", "expected"),
    [
        (0, 0, Fraction(1)),
        (1, 1, Fraction(99, 100)),  # sqrt(2) is truncated to 1 px, as in Similo
        (30, 40, Fraction(1, 2)),
        (100, 0, Fraction(0)),
        (150, 150, Fraction(0)),
    ],
)
def test_location_similarity(dx, dy, expected):
    assert (
        location_similarity((10, 10, 50, 30), (10 + dx, 10 + dy, 50 + dx, 30 + dy))
        == expected
    )


def test_area_and_shape_similarity():
    wide = (0, 0, 100, 20)
    assert area_similarity(wide, (0, 0, 50, 20)) == Fraction(1, 2)
    assert shape_similarity(wide, (0, 0, 50, 20)) == Fraction(1, 2)
    # Rotated: same area, very different shape (5 vs 1/5).
    assert area_similarity(wide, (0, 0, 20, 100)) == 1
    assert shape_similarity(wide, (0, 0, 20, 100)) == Fraction(1, 25)


# --- ranking, determinism and the sum property --------------------------------------

POOL = [
    candidate("a", USERNAME),
    candidate("b", PASSWORD),
    candidate("c", LOGIN_BUTTON),
    candidate("d", USERNAME, automationId="QApplication.loginWindow.userNameField"),
    candidate("e", USERNAME, bounds=(120, 380, 320, 404)),
    candidate("f", PASSWORD, name=None, nearestLabel=None),
    candidate("g", LOGIN_BUTTON, bounds=(0, 0, 0, 0)),
    candidate("h", PASSWORD),
]


def test_rank_returns_top_k():
    assert len(rank(USERNAME, POOL)) == 3
    assert ranked_ids(rank(USERNAME, POOL, k=1)) == ["a"]
    assert len(rank(USERNAME, POOL, k=100)) == len(POOL)
    assert rank(USERNAME, POOL, k=0) == []


def test_shuffled_candidates_give_the_same_ranking():
    expected = rank(USERNAME, POOL, k=len(POOL))
    ids = ranked_ids(expected)
    # identical > renamed id (33/38 on automationId) > moved 300 px (18/19 overall)
    assert ids[:3] == ["a", "d", "e"]
    # "b" and "h" are equal copies of PASSWORD: adjacent, in id order.
    assert ids.index("h") == ids.index("b") + 1

    for seed in range(20):
        shuffled = POOL[:]
        random.Random(seed).shuffle(shuffled)
        assert rank(USERNAME, shuffled, k=len(POOL)) == expected


def test_same_input_gives_same_output():
    assert score(USERNAME, PASSWORD) == score(USERNAME, PASSWORD)
    assert rank(PASSWORD, POOL) == rank(PASSWORD, POOL)


@pytest.mark.parametrize(
    "target", [USERNAME, PASSWORD, LOGIN_BUTTON, {"name": "Şifre"}]
)
def test_contributions_sum_exactly_to_the_score(target):
    for cand in POOL:
        result = score(target, cand)

        assert sum(result.contributions.values()) == result.score
        assert 0 <= result.score <= 1
        assert all(c >= 0 for c in result.contributions.values())
        if result.similarities:
            assert result.score == expected_score(target, cand)


# --- weights ------------------------------------------------------------------------


def test_similo_weights_cover_every_property():
    assert set(SIMILO_WEIGHTS) == set(PROPERTIES)
    assert sum(SIMILO_WEIGHTS.values()) == Fraction(19, 2)
    with pytest.raises(TypeError):
        SIMILO_WEIGHTS["name"] = Fraction(1)  # read-only


def test_custom_weights_replace_the_whole_table():
    renamed = candidate(
        "e1", USERNAME, automationId="QApplication.loginWindow.userNameField"
    )

    only_id = score(USERNAME, renamed, weights={"automationId": 1})

    assert list(only_id.contributions) == ["automationId"]
    assert only_id.score == only_id.similarities["automationId"]


def test_float_weights_are_read_as_decimals():
    target = {"name": "abc", "controlType": "Button"}
    cand = {"name": "abd", "controlType": "Edit"}

    result = score(target, cand, weights={"name": 0.1, "controlType": 0.3})

    # (0.1 * 2/3 + 0.3 * 0) / 0.4 = 1/6 exactly.
    assert result.score == Fraction(1, 6)


def test_all_zero_weights_score_zero():
    assert score(USERNAME, USERNAME, weights={}).score == 0


# --- invalid input ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("weights", "error"),
    [
        ({"label": 1}, ValueError),
        ({"name": -1}, ValueError),
        ({"name": float("nan")}, ValueError),
        ({"name": True}, TypeError),
        ({"name": "1"}, TypeError),
    ],
)
def test_invalid_weights_are_rejected(weights, error):
    with pytest.raises(error):
        score(USERNAME, USERNAME, weights=weights)


def test_invalid_candidates_are_rejected():
    with pytest.raises(ValueError, match="id"):
        rank(USERNAME, [dict(USERNAME)])
    with pytest.raises(ValueError, match="duplicate"):
        rank(USERNAME, [candidate("x", USERNAME), candidate("x", PASSWORD)])
    with pytest.raises(ValueError, match="k"):
        rank(USERNAME, POOL, k=-1)


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"bounds": (1, 2, 3)}, ValueError),
        ({"bounds": "1,2,3,4"}, ValueError),
        ({"bounds": (0, 0, "10", 10)}, TypeError),
        ({"siblingIndex": "1"}, TypeError),
        ({"name": 42}, TypeError),
    ],
)
def test_invalid_property_values_are_rejected(changes, error):
    with pytest.raises(error):
        score(USERNAME, {**USERNAME, **changes})
