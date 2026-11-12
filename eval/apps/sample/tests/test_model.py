"""The sample app's rules, tested without a display (#33).

Every behaviour the reference scenarios depend on is pinned here, so a rebuilt screen
cannot change it silently and so macOS runs the same checks Windows does.
"""

from __future__ import annotations

import model
import texts as t

# --- login (SC-14, SC-21) ------------------------------------------------------------------


def test_the_right_credentials_are_welcomed_by_name():
    # SC-14 verifies that the status text *contains the user name*, so the message cannot
    # become a bare "Welcome".
    result = model.authenticate("admin", "admin")
    assert result.ok
    assert "admin" in result.message


def test_a_wrong_password_is_refused_without_saying_which_half_was_wrong():
    assert model.authenticate("admin", "wrong") == model.LoginResult(
        ok=False, message=t.LOGIN_INVALID
    )
    assert model.authenticate("hasan", "admin").message == t.LOGIN_INVALID


def test_an_empty_field_has_its_own_message():
    assert model.authenticate("", "admin").message == t.LOGIN_EMPTY
    assert model.authenticate("admin", "").message == t.LOGIN_EMPTY


# --- the search (SC-18) --------------------------------------------------------------------


def test_a_name_is_found_as_a_substring_of_either_name():
    assert [c.first_name for c in model.search_customers("Yılmaz")] == [
        "Ayşe",
        "Mustafa",
    ]
    assert [c.last_name for c in model.search_customers("Ayşe")] == ["Yılmaz"]


def test_the_search_is_case_insensitive_the_turkish_way():
    # "YILMAZ".lower() is "yilmaz" in Python, with a dotted i, which would not match
    # "Yılmaz". SC-18 types exactly this name, so the fold has to be Turkish-aware.
    assert model.search_customers("YILMAZ") == model.search_customers("Yılmaz")
    assert model.search_customers("ayşe") == model.search_customers("AYŞE")
    assert model.fold("İSTANBUL") == "istanbul"
    assert model.fold("IŞIK") == "ışık"


def test_an_empty_query_lists_everyone():
    assert len(model.search_customers("")) == len(model.CUSTOMERS)


def test_the_city_filter_and_the_active_switch_narrow_the_result():
    ankara = model.search_customers(city="Ankara")
    assert {c.city for c in ankara} == {"Ankara"}
    assert all(c.active for c in model.search_customers(active_only=True))
    # The two together, which is what the filters do on the screen.
    assert model.search_customers(city="İzmir", active_only=True) == []


def test_a_query_that_matches_nothing_gives_no_rows():
    assert model.search_customers("Smith") == []


def test_the_status_column_is_the_turkish_word_for_the_flag():
    assert model.Customer("A", "B", "Ankara", True).status == "Etkin"
    assert model.Customer("A", "B", "Ankara", False).status == "Pasif"


# --- the detail form (SC-34) ---------------------------------------------------------------


def test_the_name_is_required_and_whitespace_is_not_a_name():
    assert model.validate_detail("", "") == [t.DETAIL_NAME_REQUIRED]
    assert model.validate_detail("   ", "") == [t.DETAIL_NAME_REQUIRED]


def test_an_e_mail_is_optional_but_has_to_look_like_one():
    assert model.validate_detail("Ayşe Yılmaz", "") == []
    assert model.validate_detail("Ayşe Yılmaz", "ayse@ayna.local") == []
    assert model.validate_detail("Ayşe Yılmaz", "ayse.ayna") == [t.DETAIL_EMAIL_INVALID]


def test_both_rules_can_fail_at_once():
    assert model.validate_detail("", "nope") == [
        t.DETAIL_NAME_REQUIRED,
        t.DETAIL_EMAIL_INVALID,
    ]


# --- the wizard (SC-20) --------------------------------------------------------------------


def test_the_summary_contains_the_chosen_department():
    # SC-20's Verify step is `name contains "Kalite Güvence"` on this label.
    summary = model.wizard_summary("Ayşe Çelik", "Kalite Güvence", "Mühendis")
    assert "Kalite Güvence" in summary
    assert "Ayşe Çelik" in summary


def test_the_department_items_keep_their_turkish_spelling():
    # SC-20 selects an item *by its text*, so these strings are part of the contract.
    assert model.DEPARTMENTS[0] == "Kalite Güvence"
    assert all(item.strip() == item for item in model.DEPARTMENTS)


def test_the_first_city_item_means_no_filter():
    assert model.CITIES[0] == model.ALL_CITIES
    assert model.ALL_CITIES not in model.CITIES[1:]
