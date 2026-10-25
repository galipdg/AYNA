"""Credential rules of the trial app. Runs on any OS, no display needed."""

from __future__ import annotations

import pytest

from app import (
    EMPTY_MESSAGE,
    INVALID_MESSAGE,
    VALID_PASSWORD,
    VALID_USERNAME,
    WELCOME_MESSAGE,
    authenticate,
)


def test_valid_credentials_welcome() -> None:
    result = authenticate(VALID_USERNAME, VALID_PASSWORD)
    assert result.ok is True
    assert result.message == WELCOME_MESSAGE
    assert "Welcome" in result.message


def test_wrong_password_is_rejected() -> None:
    result = authenticate(VALID_USERNAME, "wrong")
    assert result.ok is False
    assert result.message == INVALID_MESSAGE


def test_unknown_username_is_rejected() -> None:
    result = authenticate("someone", VALID_PASSWORD)
    assert result.ok is False
    assert result.message == INVALID_MESSAGE


@pytest.mark.parametrize(
    ("username", "password"),
    [("", ""), ("", VALID_PASSWORD), (VALID_USERNAME, "")],
)
def test_empty_fields_get_their_own_message(username: str, password: str) -> None:
    result = authenticate(username, password)
    assert result.ok is False
    assert result.message == EMPTY_MESSAGE


def test_credentials_are_case_sensitive() -> None:
    assert authenticate("Admin", VALID_PASSWORD).ok is False
    assert authenticate(VALID_USERNAME, "Admin").ok is False
