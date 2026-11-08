"""Finding the element a repository object means, in a window as it is right now (#26, #40).

A step names its target by a logical name (`login.loginButton`); the request carries that
object's **primary** property set and, when it has one, its **fallback** set (#25). Resolution
is then one question: which elements of this window have every one of those properties?

Three answers, and all three are different outcomes:

- **exactly one** -- the element to act on;
- **none** -- try the fallback set, and if that also finds none, the step failed to find its
  target (FR-35 "element not found");
- **more than one** -- also a failure, never a guess. UI Automation does not promise a stable
  child order between runs, so "the first match" would act on a different element on different
  days; the same test would then look flaky when it is the *object* that is under-specified,
  and RQ2 (#69) would measure AYNA's own nondeterminism instead of the application's. The
  answer is another property on the object, which is what the message says. Decided in the
  review of PR #187.

The fallback set is tried **only** when the primary set matches nothing. A fallback replaces a
primary set; it cannot narrow one, so it has nothing to offer when the primary set is ambiguous.

Descriptors arrive from :func:`ayna_agent.model.describe_tree` -- the same derivation a
snapshot uses -- so an object matches against the values it was stored with, including the
computed ones (`parentPath`, `siblingIndex`, `nearestLabel`), rather than against a second
rule that happens to look similar. Nothing here touches pywinauto: the live elements are
opaque and only passed through, which is what lets every rule in this module be tested with
fakes off Windows (`agent/AGENTS.md`).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ayna_agent.model import JSON_NAMES, NEVER_MATCH, Element

#: camelCase key -> the `Element` attribute it names.
_ATTRIBUTE: dict[str, str] = {camel: snake for snake, camel in JSON_NAMES.items()}

#: Properties a target may be matched on: every descriptor property except the ones that can
#: never identify an element (`model.NEVER_MATCH`: geometry, state, session-scoped handles and
#: the label's provenance). The server refuses these in a property set too
#: (`RepoObjectService.NEVER_MATCH`), so a request carrying one is a client bug, not a tester's
#: mistake -- hence an error rather than a silently ignored key, which would *widen* the match
#: and could act on the wrong element.
MATCHABLE: frozenset[str] = frozenset(
    JSON_NAMES[snake] for snake in JSON_NAMES if snake not in NEVER_MATCH
)


class Unsupported(Exception):
    """A property set names something playback cannot match on."""

    def __init__(self, properties: Sequence[str]) -> None:
        self.properties = list(properties)
        allowed = ", ".join(sorted(MATCHABLE))
        super().__init__(
            f"cannot match on {', '.join(self.properties)}; use one of: {allowed}"
        )


class NotFound(Exception):
    """No element has every property of the primary set, nor of the fallback set."""

    def __init__(self, name: str, tried: Sequence[Mapping[str, Any]]) -> None:
        self.name = name
        self.tried = [dict(properties) for properties in tried]
        sets = " or ".join(_describe(properties) for properties in self.tried)
        super().__init__(f"no element matches {name} ({sets})")


class Ambiguous(Exception):
    """More than one element has every property of the set that was tried."""

    def __init__(
        self, name: str, properties: Mapping[str, Any], count: int, which: str
    ) -> None:
        self.name = name
        self.properties = dict(properties)
        self.count = count
        self.which = which
        super().__init__(
            f"{count} elements match {name} ({_describe(self.properties)}), so AYNA cannot "
            f"tell which one you mean; add another property to the object's "
            f"{'Find by' if which == 'primary' else 'Backup'} set"
        )


@dataclass(frozen=True, slots=True)
class Resolution:
    """The one element a target resolved to, and how."""

    #: The live element, opaque here; `playback.actions` acts on it.
    element: Any
    descriptor: Element
    #: Its position in the walked tree, for messages and for the decision log (#63).
    index: int
    #: `"primary"` or `"fallback"` -- which set matched. A fallback match means the object's
    #: Find-by properties have stopped matching, which is what #73 heals and #63 logs.
    which: str


def _describe(properties: Mapping[str, Any]) -> str:
    if not properties:
        return "no properties"
    return ", ".join(f"{key}={value!r}" for key, value in sorted(properties.items()))


def check_properties(properties: Mapping[str, Any]) -> None:
    """Raise `Unsupported` unless every key can identify an element, and there is at least one.

    An empty set is refused because it matches every element in the window, which reads as
    "ambiguous" when the real problem is that the object says nothing.
    """
    if not properties:
        raise Unsupported(["(an empty property set)"])
    unknown = [key for key in properties if key not in MATCHABLE]
    if unknown:
        raise Unsupported(sorted(unknown))


def matches(descriptor: Element, properties: Mapping[str, Any]) -> bool:
    """True when the descriptor has **every** property, compared exactly.

    Text is compared case-sensitively and without trimming, as the step schema's checkpoints
    are: a Turkish label differing only in case is a different label, and a tester who sees
    trailing space in the Spy should be able to match it. A property the element does not have
    is `None`, which equals no expected value, so a missing property never matches.
    """
    for key, expected in properties.items():
        if getattr(descriptor, _ATTRIBUTE[key], None) != expected:
            return False
    return True


def find_matches(
    descriptors: Sequence[Element],
    infos: Sequence[Any],
    properties: Mapping[str, Any],
) -> list[Resolution]:
    """Every element matching `properties`, in tree order. Raises `Unsupported` for a bad set.

    Returns **all** of them rather than the first, because "more than one" is an answer the
    caller has to be able to give.
    """
    check_properties(properties)
    return [
        Resolution(element=infos[index], descriptor=descriptor, index=index, which="")
        for index, descriptor in enumerate(descriptors)
        if matches(descriptor, properties)
    ]


def resolve(
    descriptors: Sequence[Element],
    infos: Sequence[Any],
    name: str,
    primary: Mapping[str, Any],
    fallback: Mapping[str, Any] | None = None,
) -> Resolution:
    """The single element `name` resolves to.

    Raises `Ambiguous` when a set matches several elements, `NotFound` when neither set matches
    any, and `Unsupported` when a set names a property playback cannot match on.
    """
    tried: list[Mapping[str, Any]] = []
    for which, properties in (("primary", primary), ("fallback", fallback or None)):
        if not properties:
            continue
        tried.append(properties)
        found = find_matches(descriptors, infos, properties)
        if len(found) > 1:
            raise Ambiguous(name, properties, len(found), which)
        if found:
            one = found[0]
            return Resolution(
                element=one.element,
                descriptor=one.descriptor,
                index=one.index,
                which=which,
            )
    raise NotFound(name, tried)
