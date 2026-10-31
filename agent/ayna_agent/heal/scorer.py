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
- ``bounds``: ``(left, top, right, bottom)`` in physical pixels, virtual-desktop
  coordinates, as UI Automation reports them to a per-monitor-v2 DPI aware agent
  (Win32 ``RECT`` order, as in the #6 UIA dump). Floats are rounded to whole pixels.
- ``dpi``: DPI of the element's window (``GetDpiForWindow``; 96 = 100 % scaling).
  Not scored itself: location and area are compared in device-independent pixels
  (DIP, physical * 96 / dpi), so the same layout scores the same at every display
  scaling, also when the target and the candidate come from machines with different
  scaling. When only one of the two has ``dpi``, the other is taken to have the same
  (one machine, as before ``dpi`` existed), so an unchanged control still matches
  itself; when neither has it, both are taken as 96, which compares raw pixels as
  before. ``bounds`` stay physical everywhere else.
- ``parentPath``: the ancestor chain as one string, root first, built from the
  programmatic ControlType names joined by ``/`` (e.g. ``"Window/Pane/Group"``), never
  from the localised control type: a Turkish Windows would give ``Pencere/Bölme/Grup``
  and zero this property against an English one. #43 builds it.
- ``siblingIndex``: position among the parent's children.
- ``nearestLabel``: text of the label that names the element.
- ``windowTitle``: title of the element's top-level window.

Candidates passed to :func:`rank` also need ``id`` (the snapshot element id), used to
report the candidate and to break ties. These types must be aligned with the element
descriptor (#11) and the snapshot (#12) when they land.

Missing-property rule: a value is missing when the key is absent, the value is ``None``,
a string is blank after normalisation, or the bounds are empty (width or height <= 0,
which UI Automation reports for off-screen elements; this counts for location, area and
shape together).

- Target lacks the value: the property is skipped (nothing to compare against). Its
  weight is left out of both sums.
- Target has it, candidate lacks it: similarity 0 and the weight *is* counted, as in
  Similo, where a missing attribute is simply no match. Otherwise an unnamed control
  would outrank a named one whose name differs only a little.

If the target has nothing to compare, the score is 0 and there are no contributions.

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
automationId   Id                        1.5     normalised Levenshtein of the last segment
name           Visible text              1.5     normalised Levenshtein
controlType    Tag                       1.5     equals (case-insensitive)
nearestLabel   Neighbor texts            1.5     shared-word ratio
className      Class                     0.5     normalised Levenshtein
parentPath     XPath (absolute)          0.5     normalised Levenshtein
siblingIndex   XPath (id-relative)       0.5     equals
location       Location                  0.5     1 - d / 100 DIP, 0 beyond 100 DIP
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
  whitespace collapsed. Other diacritics stay significant (``ş`` != ``s``). The one
  exception: a combining dot above (U+0307) that is still a separate character after
  NFC is dropped, wherever it is. That is what folding ``İ`` leaves, and also a dot
  on a letter with no precomposed dotted form; ``ż`` and ``ė`` are single characters
  and keep their dot.
- Normalised Levenshtein: ``1 - distance / max(len_a, len_b)``.
- ``automationId`` compares only its leaf, the text after the last ``.`` (ids without a
  dot compare whole), with normalised Levenshtein. Qt builds AutomationId as a dotted
  path over the whole object chain, so a renamed ancestor changes every descendant's id
  (``memory-bank/learnings.md``, 2026-10-25), and siblings share a long prefix that
  would make unrelated ids look alike. The ancestor chain is already scored by
  ``parentPath``. Similo uses exact match; the edit distance gives partial credit to a
  renamed leaf (``usernameInput`` -> ``userNameField``).
- Shared-word ratio: ``|common words| / max(|words_a|, |words_b|)`` over the sets of
  word tokens, as the paper describes it ("5 common words out of 10 gives 0.5"). The
  authors' code weights words by length and accepts prefix matches; v0 keeps the paper's
  simpler definition.
- Location, area and shape follow the authors' code (github.com/michelnass/Similo2,
  ``WidgetLocator.java``: ``calcSimilarityScore``, ``integerSimilarity``), because the
  paper does not say how they are normalised: the top-left corners' distance is
  truncated to whole pixels, and area / shape use ``min / max``. AYNA measures distance
  and area in DIP (``dpi`` above): Similo's 100 px cut-off was set for web pages, whose
  CSS pixels are device-independent too. Shape does not change with scaling.

Differences from Similo: Similo's score is an unnormalised weighted sum; this one is
divided by the weights of the properties the target has (issue #49), so it lies in
[0, 1] and is comparable across targets. No minimum score is applied here: like Similo, ``rank``
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
from typing import Required, TypedDict, TypeVar


class Element(TypedDict, total=False):
    """Properties of one UI element; every key is optional (see the module docstring)."""

    automationId: str
    name: str
    controlType: str
    className: str
    bounds: Sequence[int | float]
    dpi: int
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

#: Similo's location cut-off: corners this far apart (or more), in device-independent
#: pixels, have similarity 0.
LOCATION_CUTOFF_DIP = 100

#: The DPI at which a physical pixel is one device-independent pixel (100 % scaling).
BASE_DPI = 96


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


def location_similarity(
    a: Rect, b: Rect, dpi_a: int = BASE_DPI, dpi_b: int = BASE_DPI
) -> Fraction:
    """1 for the same top-left corner, falling linearly to 0 at 100 DIP apart.

    ``a`` and ``b`` are physical pixels at ``dpi_a`` and ``dpi_b``; the corners are
    converted to device-independent pixels before the distance is taken.
    """
    dx = _dip(a[0], dpi_a) - _dip(b[0], dpi_b)
    dy = _dip(a[1], dpi_a) - _dip(b[1], dpi_b)
    squared = dx * dx + dy * dy
    # floor(sqrt(x)) == isqrt(floor(x)) for x >= 0, so the truncation stays exact.
    distance = math.isqrt(squared.numerator // squared.denominator)
    return Fraction(max(LOCATION_CUTOFF_DIP - distance, 0), LOCATION_CUTOFF_DIP)


def area_similarity(
    a: Rect, b: Rect, dpi_a: int = BASE_DPI, dpi_b: int = BASE_DPI
) -> Fraction:
    """Smaller area divided by the larger one, both in square DIP."""
    return _ratio(
        _width(a) * _height(a) * Fraction(BASE_DPI, dpi_a) ** 2,
        _width(b) * _height(b) * Fraction(BASE_DPI, dpi_b) ** 2,
    )


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


def _dpi(element: Element) -> int | None:
    value = element.get("dpi")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"'dpi' must be an int, got {value!r}")
    if value <= 0:
        raise ValueError(f"'dpi' must be > 0, got {value}")
    return value


def _dpis(target: Element, candidate: Element) -> tuple[int, int]:
    """Both DPIs. One missing takes the other's value; both missing are 96.

    Defaulting a single missing side to 96 would make an unchanged control off 100 %
    scaling look moved and resized (the #166 review).
    """
    target_dpi, candidate_dpi = _dpi(target), _dpi(candidate)
    if target_dpi is None:
        target_dpi = candidate_dpi or BASE_DPI
    if candidate_dpi is None:
        candidate_dpi = target_dpi
    return target_dpi, candidate_dpi


def _dip(pixel: int, dpi: int) -> Fraction:
    return Fraction(pixel * BASE_DPI, dpi)


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


_T = TypeVar("_T")


def _apply_missing_rule(
    target_value: _T | None,
    candidate_value: _T | None,
    similarity: Callable[[_T, _T], Fraction],
) -> Fraction | None:
    """Skip when the target lacks the value; score 0 when only the candidate lacks it."""
    if target_value is None:
        return None
    if candidate_value is None:
        return Fraction(0)
    return similarity(target_value, candidate_value)


def _compare_text(prop: str, similarity: Callable[[str, str], Fraction]) -> Comparator:
    def compare(target: Element, candidate: Element) -> Fraction | None:
        return _apply_missing_rule(
            _text(target, prop), _text(candidate, prop), similarity
        )

    return compare


def _compare_bounds(
    similarity: Callable[[Rect, Rect, int, int], Fraction],
) -> Comparator:
    def compare(target: Element, candidate: Element) -> Fraction | None:
        return _apply_missing_rule(
            _bounds(target),
            _bounds(candidate),
            lambda a, b: similarity(a, b, *_dpis(target, candidate)),
        )

    return compare


def _equal(a: str, b: str) -> Fraction:
    return Fraction(int(a == b))


def automation_id_similarity(a: str, b: str) -> Fraction:
    """Normalised Levenshtein of the ids' last dotted segments (normalised strings)."""
    return text_similarity(_leaf(a), _leaf(b))


def _leaf(automation_id: str) -> str:
    # "qapplication.loginwindow.usernameinput" -> "usernameinput"; a trailing dot keeps
    # the whole id so that the result is never empty.
    return automation_id.rsplit(".", 1)[-1] or automation_id


def _sibling_index(element: Element) -> int | None:
    value = element.get("siblingIndex")
    if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
        raise TypeError(f"'siblingIndex' must be an int, got {value!r}")
    return value


def _compare_sibling_index(target: Element, candidate: Element) -> Fraction | None:
    return _apply_missing_rule(
        _sibling_index(target),
        _sibling_index(candidate),
        lambda a, b: Fraction(int(a == b)),
    )


_COMPARATORS: Mapping[str, Comparator] = MappingProxyType(
    {
        "automationId": _compare_text("automationId", automation_id_similarity),
        "name": _compare_text("name", text_similarity),
        "controlType": _compare_text("controlType", _equal),
        "nearestLabel": _compare_text("nearestLabel", word_similarity),
        "className": _compare_text("className", text_similarity),
        "parentPath": _compare_text("parentPath", text_similarity),
        "siblingIndex": _compare_sibling_index,
        "location": _compare_bounds(location_similarity),
        "area": _compare_bounds(area_similarity),
        # Scaling does not change a shape, so the DPIs are not needed.
        "shape": _compare_bounds(lambda a, b, _dpi_a, _dpi_b: shape_similarity(a, b)),
        "windowTitle": _compare_text("windowTitle", text_similarity),
    }
)
