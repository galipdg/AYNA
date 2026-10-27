"""Self-healing scorer v0 (#49): weighted, explainable similarity between two elements.

When a repository object no longer resolves, candidate generation (#42) collects the
elements of the new snapshot that could be it, and this module ranks them against the
element stored for the object (the *target*):

    S = sum(w_i * sim_i) / sum(w_i)     over the properties compared for this pair

Each ``sim_i`` is in [0, 1]. The result carries the per-property contributions
``w_i * sim_i / sum(w_i)``, which sum to ``S``; the approval screen (#75) can show them
as they are (contribution C2 in ``memory-bank/project/brief.md``).

Input contract
--------------
Elements are plain mappings (:class:`Element`). Keys follow the Element properties of
``docs/graph-model.md`` (camelCase) plus the graph-context features that #43 computes
from the snapshot:

- ``automationId``, ``name``, ``controlType``, ``className``: strings from UI Automation.
- ``bounds``: ``(left, top, right, bottom)`` in screen pixels (Win32 ``RECT`` order, as
  in the #6 UIA dump). Floats are rounded to whole pixels.
- ``parentPath``: the ancestor chain as one string (e.g. ``"Window/Pane/Group"``).
- ``siblingIndex``: position among the parent's children.
- ``nearestLabel``: text of the label that names the element.
- ``windowTitle``: title of the element's top-level window.

Candidates passed to :func:`rank` also need ``id`` (the snapshot element id), used to
report the candidate and to break ties. These types must be aligned with the element
descriptor (#11) and the snapshot (#12) when they land.

Missing-property rule: a property is compared only when *both* sides have a value. A
value is missing when the key is absent, the value is ``None``, a string is blank after
normalisation, or the bounds are empty (width or height <= 0, which UI Automation
reports for off-screen elements; then location, area and shape are all skipped). A
skipped property is left out of both sums: its weight is not counted, so it neither
lowers nor raises the score. If nothing can be compared, the score is 0 and there are
no contributions. Known v0 limitation: a candidate is not marked down for lacking a value
the target has, so an unnamed control can outrank a named one whose name differs
(``test_missing_candidate_value_is_not_penalised``; to be measured in #76).

Weights and similarities (Similo mapping)
-----------------------------------------
Starting weights are Similo's hand-set ones: 1.5 for the parameters an earlier study
found stable, 0.5 for the rest (Nass et al., "Similarity-based web element localization
for robust test automation", ACM TOSEM 32(3), 2023, sections 3.1-3.2; arXiv:2208.00677).
Similo scores 14 web locator parameters; each AYNA property below takes the weight of
its closest web analogue.

=============  ========================  ======  =========================================
AYNA property  Similo parameter          Weight  Similarity
=============  ========================  ======  =========================================
automationId   Id                        1.5     normalised Levenshtein (Similo: equals)
name           Visible text              1.5     normalised Levenshtein
controlType    Tag                       1.5     equals (case-insensitive)
nearestLabel   Neighbor texts            1.5     shared-word ratio
className      Class                     0.5     normalised Levenshtein
parentPath     XPath (absolute)          0.5     normalised Levenshtein
siblingIndex   XPath (id-relative)       0.5     equals
location       Location                  0.5     1 - d / 100 px, 0 beyond 100 px
area           Area                      0.5     min / max
shape          Shape (width / height)    0.5     min / max
windowTitle    none (AYNA addition)      0.5     normalised Levenshtein
=============  ========================  ======  =========================================

Not mapped: Similo's Name (an HTML form identifier, covered by ``automationId``; UIA
``Name`` is the visible text), HRef and Alt (no UIA analogue) and IsButton (implied by
``controlType``). ``windowTitle`` comes from #43 and has no Similo counterpart, so it
gets the lower weight.

Similarity details:

- Text is normalised before comparing: NFC, ``casefold``, Turkish dotted/dotless i
  folded together (``İ``/``I``/``ı`` -> ``i``) so that upper/lower case Turkish matches,
  whitespace collapsed. Other diacritics stay significant (``ş`` != ``s``).
- Normalised Levenshtein: ``1 - distance / max(len_a, len_b)``. ``automationId`` uses it
  instead of Similo's exact match because Qt builds AutomationId as a dotted object path
  that changes when any ancestor is renamed (``memory-bank/learnings.md``, 2026-10-25).
- Shared-word ratio: ``|common words| / max(|words_a|, |words_b|)`` over the sets of
  word tokens, as the paper describes it ("5 common words out of 10 gives 0.5"). The
  authors' code weights words by length and accepts prefix matches; v0 keeps the paper's
  simpler definition.
- Location, area and shape follow the authors' code (github.com/michelnass/Similo2,
  ``WidgetLocator.java``: ``calcSimilarityScore``, ``integerSimilarity``), because the
  paper does not say how they are normalised: the top-left corners' distance is
  truncated to whole pixels, and area / shape use ``min / max``.

Differences from Similo: Similo's score is an unnormalised weighted sum; this one is
divided by the weights of the compared properties (issue #49), so it lies in [0, 1] and
is comparable across targets. No minimum score is applied here: like Similo, ``rank``
always returns the best candidates it has, and the caller (#73) decides whether the best
one is good enough to propose.

Determinism and exactness
-------------------------
All similarities are rational, so the arithmetic uses :class:`fractions.Fraction`:
results are exact, identical on every platform, and the contributions sum to the score
exactly (no rounding policy is needed). Convert with ``float()`` at the JSON boundary.
``rank`` orders by score descending, then candidate id ascending.

Weights live in :data:`SIMILO_WEIGHTS`; pass ``weights=`` to :func:`score` / :func:`rank`
to try others (#76, RQ4).
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from types import MappingProxyType
from typing import Required, TypedDict


class Element(TypedDict, total=False):
    """Properties of one UI element; every key is optional (see the module docstring)."""

    automationId: str
    name: str
    controlType: str
    className: str
    bounds: Sequence[int | float]
    parentPath: str
    siblingIndex: int
    nearestLabel: str
    windowTitle: str


class Candidate(Element, total=False):
    """An element of the new snapshot; ``id`` identifies it in the ranking."""

    id: Required[str]


Weight = int | float | Decimal | Fraction

#: Bounds after parsing: (left, top, right, bottom) in whole pixels, non-empty.
Rect = tuple[int, int, int, int]

_STABLE = Fraction(3, 2)
_OTHER = Fraction(1, 2)

#: Similo's starting weights mapped to AYNA properties. The order is the order of
#: ``contributions`` and ``similarities`` in every result.
SIMILO_WEIGHTS: Mapping[str, Fraction] = MappingProxyType(
    {
        "automationId": _STABLE,
        "name": _STABLE,
        "controlType": _STABLE,
        "nearestLabel": _STABLE,
        "className": _OTHER,
        "parentPath": _OTHER,
        "siblingIndex": _OTHER,
        "location": _OTHER,
        "area": _OTHER,
        "shape": _OTHER,
        "windowTitle": _OTHER,
    }
)

#: Every property the scorer knows, in result order.
PROPERTIES: tuple[str, ...] = tuple(SIMILO_WEIGHTS)

#: Similo's location cut-off: corners this far apart (or more) have similarity 0.
LOCATION_CUTOFF_PX = 100


@dataclass(frozen=True)
class ScoreResult:
    """Score of one candidate against the target.

    ``contributions`` and ``similarities`` hold only the compared properties, in
    :data:`PROPERTIES` order; ``sum(contributions.values()) == score`` exactly.
    """

    score: Fraction
    contributions: Mapping[str, Fraction]
    similarities: Mapping[str, Fraction]


@dataclass(frozen=True)
class RankedCandidate:
    """One entry of :func:`rank`: the candidate's id and its score."""

    id: str
    result: ScoreResult


# --- public API -------------------------------------------------------------------


def score(
    target: Element, candidate: Element, weights: Mapping[str, Weight] | None = None
) -> ScoreResult:
    """Score ``candidate`` against ``target``.

    ``weights`` replaces :data:`SIMILO_WEIGHTS` as a whole: a property it does not name
    has weight 0 and is not compared.
    """
    return _score(target, candidate, _resolve_weights(weights))


def rank(
    target: Element,
    candidates: Iterable[Candidate],
    k: int = 3,
    weights: Mapping[str, Weight] | None = None,
) -> list[RankedCandidate]:
    """Return the ``k`` best candidates, by score descending, then id ascending."""
    if k < 0:
        raise ValueError(f"k must be >= 0, got {k}")
    resolved = _resolve_weights(weights)
    ranked: list[RankedCandidate] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate_id = candidate.get("id")
        if not isinstance(candidate_id, str) or not candidate_id:
            raise ValueError("every candidate needs a non-empty string 'id'")
        if candidate_id in seen:
            raise ValueError(f"duplicate candidate id {candidate_id!r}")
        seen.add(candidate_id)
        ranked.append(
            RankedCandidate(candidate_id, _score(target, candidate, resolved))
        )
    ranked.sort(key=lambda entry: (-entry.result.score, entry.id))
    return ranked[:k]


# --- similarity functions -----------------------------------------------------------


def normalize_text(value: str) -> str:
    """Fold case (Turkish i variants included) and whitespace; keep other diacritics."""
    folded = unicodedata.normalize("NFC", value).casefold()
    # casefold() turns "İ" into "i" + U+0307 and leaves "ı" alone; fold all to "i".
    folded = folded.replace("̇", "").replace("ı", "i")
    return " ".join(folded.split())


def levenshtein(a: str, b: str) -> int:
    """Edit distance (insert, delete, substitute; each costs 1)."""
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current = [i]
        for j, char_b in enumerate(b, start=1):
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + (char_a != char_b),
                )
            )
        previous = current
    return previous[-1]


def text_similarity(a: str, b: str) -> Fraction:
    """Normalised Levenshtein similarity of two non-empty, normalised strings."""
    longest = max(len(a), len(b))
    return Fraction(longest - levenshtein(a, b), longest)


def word_similarity(a: str, b: str) -> Fraction:
    """Shared-word ratio of two normalised strings."""
    words_a, words_b = set(_WORD.findall(a)), set(_WORD.findall(b))
    if not words_a or not words_b:
        return Fraction(int(a == b))
    return Fraction(len(words_a & words_b), max(len(words_a), len(words_b)))


def location_similarity(a: Rect, b: Rect) -> Fraction:
    """1 for the same top-left corner, falling linearly to 0 at 100 px apart."""
    distance = math.isqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)
    return Fraction(max(LOCATION_CUTOFF_PX - distance, 0), LOCATION_CUTOFF_PX)


def area_similarity(a: Rect, b: Rect) -> Fraction:
    """Smaller area divided by the larger one."""
    return _ratio(_width(a) * _height(a), _width(b) * _height(b))


def shape_similarity(a: Rect, b: Rect) -> Fraction:
    """Smaller aspect ratio (width / height) divided by the larger one."""
    return _ratio(Fraction(_width(a), _height(a)), Fraction(_width(b), _height(b)))


# --- internals ----------------------------------------------------------------------

_WORD = re.compile(r"\w+")


def _resolve_weights(weights: Mapping[str, Weight] | None) -> Mapping[str, Fraction]:
    if weights is None:
        return SIMILO_WEIGHTS
    unknown = sorted(set(weights) - set(PROPERTIES))
    if unknown:
        raise ValueError(f"unknown properties in weights: {unknown}")
    resolved: dict[str, Fraction] = {}
    for prop in PROPERTIES:
        weight = _to_fraction(weights.get(prop, 0))
        if weight < 0:
            raise ValueError(f"weight of {prop!r} must be >= 0, got {weight}")
        resolved[prop] = weight
    return resolved


def _to_fraction(value: Weight) -> Fraction:
    if isinstance(value, bool) or not isinstance(
        value, int | float | Decimal | Fraction
    ):
        raise TypeError(f"weight must be a number, got {value!r}")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"weight must be finite, got {value}")
        # str() gives the shortest decimal that round-trips, so 0.1 means 1/10.
        return Fraction(str(value))
    return Fraction(value)


def _score(
    target: Element, candidate: Element, weights: Mapping[str, Fraction]
) -> ScoreResult:
    similarities: dict[str, Fraction] = {}
    for prop in PROPERTIES:
        if weights[prop] == 0:
            continue
        similarity = _COMPARATORS[prop](target, candidate)
        if similarity is not None:
            similarities[prop] = similarity
    total_weight = sum((weights[prop] for prop in similarities), Fraction(0))
    if total_weight == 0:
        return ScoreResult(Fraction(0), {}, {})
    contributions = {
        prop: weights[prop] * similarity / total_weight
        for prop, similarity in similarities.items()
    }
    return ScoreResult(
        sum(contributions.values(), Fraction(0)), contributions, similarities
    )


def _text(element: Element, prop: str) -> str | None:
    value = element.get(prop)
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{prop!r} must be a string, got {value!r}")
    return normalize_text(value) or None


def _bounds(element: Element) -> Rect | None:
    value = element.get("bounds")
    if value is None:
        return None
    if isinstance(value, str | bytes) or len(value) != 4:
        raise ValueError(f"'bounds' must be (left, top, right, bottom), got {value!r}")
    left, top, right, bottom = (_pixel(v) for v in value)
    if right <= left or bottom <= top:
        return None
    return left, top, right, bottom


def _pixel(value: float) -> int:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"bounds coordinates must be numbers, got {value!r}")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"bounds coordinates must be finite, got {value}")
    return round(value)


def _width(bounds: Rect) -> int:
    return bounds[2] - bounds[0]


def _height(bounds: Rect) -> int:
    return bounds[3] - bounds[1]


def _ratio(a: int | Fraction, b: int | Fraction) -> Fraction:
    return Fraction(min(a, b)) / max(a, b)


Comparator = Callable[[Element, Element], Fraction | None]


def _compare_text(prop: str, similarity: Callable[[str, str], Fraction]) -> Comparator:
    def compare(target: Element, candidate: Element) -> Fraction | None:
        a, b = _text(target, prop), _text(candidate, prop)
        return None if a is None or b is None else similarity(a, b)

    return compare


def _compare_bounds(
    similarity: Callable[[Rect, Rect], Fraction],
) -> Comparator:
    def compare(target: Element, candidate: Element) -> Fraction | None:
        a, b = _bounds(target), _bounds(candidate)
        return None if a is None or b is None else similarity(a, b)

    return compare


def _equal(a: str, b: str) -> Fraction:
    return Fraction(int(a == b))


def _compare_sibling_index(target: Element, candidate: Element) -> Fraction | None:
    a, b = target.get("siblingIndex"), candidate.get("siblingIndex")
    if a is None or b is None:
        return None
    for value in (a, b):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"'siblingIndex' must be an int, got {value!r}")
    return Fraction(int(a == b))


_COMPARATORS: Mapping[str, Comparator] = MappingProxyType(
    {
        "automationId": _compare_text("automationId", text_similarity),
        "name": _compare_text("name", text_similarity),
        "controlType": _compare_text("controlType", _equal),
        "nearestLabel": _compare_text("nearestLabel", word_similarity),
        "className": _compare_text("className", text_similarity),
        "parentPath": _compare_text("parentPath", text_similarity),
        "siblingIndex": _compare_sibling_index,
        "location": _compare_bounds(location_similarity),
        "area": _compare_bounds(area_similarity),
        "shape": _compare_bounds(shape_similarity),
        "windowTitle": _compare_text("windowTitle", text_similarity),
    }
)
