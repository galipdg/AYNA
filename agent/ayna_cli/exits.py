"""What `ayna run` exits with, and the rule for choosing (FR-23)."""

from __future__ import annotations

#: Every test passed and every result was delivered.
ALL_GOOD = 0

#: A test failed, or a step proposed a repair (#73). The run itself worked.
TEST_FAILED = 1

#: The command could not do its job: the suite could not be read, the agent could not start,
#: the server was unreachable, the token was refused, or a result was not delivered. **This
#: wins over a green suite**: FR-23 says so in as many words, because a passing run nobody
#: recorded is not a passing run anybody can point at later.
OPERATIONAL_FAILURE = 2


def exit_code(*, any_test_failed: bool, operational_failure: bool) -> int:
    """The one place the precedence lives, so no caller has to remember it."""
    if operational_failure:
        return OPERATIONAL_FAILURE
    return TEST_FAILED if any_test_failed else ALL_GOOD
