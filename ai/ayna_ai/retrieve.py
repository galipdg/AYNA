"""Repository objects that a Turkish instruction may refer to.

The service (`ayna_ai.service`) asks a `Retriever` for the candidate objects
of one request and lets the generator choose step targets only among them.
Until vector + graph retrieval exists (#58), `PassThroughRetriever` uses the
objects the caller sends with the request.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RetrievalQuery:
    text: str  # the Turkish instruction
    app: str  # application under test
    version: str | None = None  # application version
    screen: str | None = None  # screen the user is writing the test for
    objects: Mapping[str, str] | None = None  # caller's candidates: name -> description


class RetrievalInputError(ValueError):
    """The query lacks what the retriever needs; the caller must fix the request."""


class Retriever(Protocol):
    def retrieve(self, query: RetrievalQuery) -> dict[str, str]:
        """Candidate objects, logical name -> Turkish description, best first.

        Step targets are limited to exactly these names, so a retriever must
        return only objects that exist in the repository.
        """
        ...


class PassThroughRetriever:
    """Uses the request's own objects (stand-in until #58)."""

    def retrieve(self, query: RetrievalQuery) -> dict[str, str]:
        if not query.objects:
            raise RetrievalInputError(
                "objects is required: the service has no repository retrieval yet (#58)"
            )
        return dict(query.objects)
