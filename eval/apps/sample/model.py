"""The sample app's rules, with no Qt in sight (#33).

Everything a test or a screen needs to *decide* lives here: credentials, the customer
search, the detail form's validation and the wizard's summary line. The widget layer in
`windows.py` only renders what these functions return, so the behaviour the reference
scenarios depend on (`docs/rs/scenarios.md` §C.2) can be tested on macOS, without a
display, and stays the same when a screen is rebuilt.

The bug-injected versions (#47) change exactly one of these functions each, which is why
they are small and separate.
"""

from __future__ import annotations

from dataclasses import dataclass

from texts import (
    DETAIL_EMAIL_INVALID,
    DETAIL_NAME_REQUIRED,
    LOGIN_EMPTY,
    LOGIN_INVALID,
    LOGIN_WELCOME,
    WIZARD_SUMMARY,
)

VALID_USERNAME = "admin"
VALID_PASSWORD = "admin"

#: Turkish letters whose case mapping differs from the Latin default. `str.lower()` turns
#: "YILMAZ" into "yilmaz", so a search for "Yılmaz" would not find it: the dotted and the
#: dotless i are different letters in Turkish. Searching is the one place in this app where
#: that is visible to a test, and SC-18 types exactly "Yılmaz".
_FOLD = str.maketrans(
    {"I": "ı", "İ": "i", "Ş": "ş", "Ğ": "ğ", "Ü": "ü", "Ö": "ö", "Ç": "ç"}
)


def fold(text: str) -> str:
    """Lower-case `text` the way a Turkish user expects, for case-insensitive matching."""
    return text.translate(_FOLD).lower()


@dataclass(frozen=True)
class LoginResult:
    """Outcome of a credential check and the message the status label shows."""

    ok: bool
    message: str


def authenticate(username: str, password: str) -> LoginResult:
    """Check credentials. The welcome message contains the user name, as SC-14 asserts."""
    if not username or not password:
        return LoginResult(ok=False, message=LOGIN_EMPTY)
    if username == VALID_USERNAME and password == VALID_PASSWORD:
        return LoginResult(ok=True, message=LOGIN_WELCOME.format(user=username))
    return LoginResult(ok=False, message=LOGIN_INVALID)


@dataclass(frozen=True)
class Customer:
    """One row of the list screen's grid."""

    first_name: str
    last_name: str
    city: str
    active: bool

    @property
    def status(self) -> str:
        return "Etkin" if self.active else "Pasif"


#: The seed rows. Deliberately small (NFR-02 wants a 2 s snapshot of every window) and
#: deliberately Turkish: SC-20 requires Turkish characters to survive the whole chain, and
#: `eval/nl/` writes its sentences against these values.
CUSTOMERS: tuple[Customer, ...] = (
    Customer("Ayşe", "Yılmaz", "Ankara", True),
    Customer("Mehmet", "Demir", "İstanbul", True),
    Customer("Zeynep", "Kaya", "İzmir", False),
    Customer("Mustafa", "Yılmaz", "Bursa", True),
    Customer("Elif", "Şahin", "Ankara", True),
    Customer("Can", "Öztürk", "İstanbul", False),
)

#: The city filter's items; the first one means "no filter".
ALL_CITIES = "Tümü"
CITIES: tuple[str, ...] = (ALL_CITIES, "Ankara", "İstanbul", "İzmir", "Bursa")


def search_customers(
    query: str = "",
    city: str = ALL_CITIES,
    active_only: bool = False,
    customers: tuple[Customer, ...] = CUSTOMERS,
) -> list[Customer]:
    """The rows a search shows: a name match, a city and an "active only" switch.

    `query` matches either name, case-insensitively and Turkish-aware (`fold`), as a
    substring; an empty query matches every row.
    """
    needle = fold(query.strip())
    rows = []
    for customer in customers:
        if needle and needle not in fold(f"{customer.first_name} {customer.last_name}"):
            continue
        if city != ALL_CITIES and customer.city != city:
            continue
        if active_only and not customer.active:
            continue
        rows.append(customer)
    return rows


#: The detail form's and the wizard's department items. "Kalite Güvence" is the one SC-20
#: selects by text, so it must stay spelled exactly like this.
DEPARTMENTS: tuple[str, ...] = (
    "Kalite Güvence",
    "Yazılım Geliştirme",
    "Sistem Mühendisliği",
    "Test ve Doğrulama",
)

ROLES: tuple[str, ...] = ("Mühendis", "Uzman", "Yönetici")


def validate_detail(name: str, email: str) -> list[str]:
    """The detail form's rules: a required name, and an e-mail that looks like one.

    Returns the messages to show, empty when the form may be saved. The "missing
    validation" bug version (#47, SC-34) drops the first rule and nothing else.
    """
    problems = []
    if not name.strip():
        problems.append(DETAIL_NAME_REQUIRED)
    if email.strip() and "@" not in email:
        problems.append(DETAIL_EMAIL_INVALID)
    return problems


def wizard_summary(name: str, department: str, role: str) -> str:
    """The wizard's third page. SC-20 checks that it contains the chosen department."""
    return WIZARD_SUMMARY.format(name=name.strip(), department=department, role=role)
