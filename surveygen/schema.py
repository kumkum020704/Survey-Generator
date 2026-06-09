"""Survey definition: loading and validation.

The schema is deliberately generic so the generator is not hard-wired to the
e-commerce demo survey. A survey is a title plus an ordered list of questions.
Each question has a ``type`` (how it is answered) and an optional ``role``
(what it *means*). Roles let the coherence engine wire questions into a causal
model; questions without a recognised role fall back to plausible, independent
sampling so any survey still produces sensible output.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

# Supported answer formats.
VALID_TYPES = {"rating", "nps", "single_choice", "open_text"}

# Semantic roles the coherence engine understands. Anything else is treated as
# a generic question of its ``type``.
KNOWN_ROLES = {
    "satisfaction",      # rating that reflects overall sentiment
    "nps",               # 0-10 likelihood-to-recommend
    "category",          # what was purchased
    "delivery_on_time",  # Yes/No fulfilment signal
    "open_feedback",     # free-text improvement prompt
}


@dataclass
class Question:
    id: str
    text: str
    type: str
    role: str | None = None
    scale: tuple[int, int] | None = None
    options: list[str] | None = None

    def __post_init__(self) -> None:
        if self.type not in VALID_TYPES:
            raise ValueError(
                f"Question {self.id!r}: unsupported type {self.type!r}. "
                f"Expected one of {sorted(VALID_TYPES)}."
            )

        if self.type in ("rating", "nps"):
            if not self.scale or len(self.scale) != 2:
                raise ValueError(
                    f"Question {self.id!r}: {self.type} questions need a "
                    f"two-element 'scale', e.g. [1, 5]."
                )
            lo, hi = self.scale
            if lo >= hi:
                raise ValueError(
                    f"Question {self.id!r}: scale low ({lo}) must be < high ({hi})."
                )

        if self.type == "single_choice":
            if not self.options or len(self.options) < 2:
                raise ValueError(
                    f"Question {self.id!r}: single_choice needs at least two 'options'."
                )

    @property
    def is_numeric(self) -> bool:
        return self.type in ("rating", "nps")


@dataclass
class Survey:
    title: str
    questions: list[Question]
    description: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.questions:
            raise ValueError("Survey must contain at least one question.")
        ids = [q.id for q in self.questions]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(f"Duplicate question ids: {sorted(dupes)}")

    def question(self, qid: str) -> Question | None:
        return next((q for q in self.questions if q.id == qid), None)

    def by_role(self, role: str) -> Question | None:
        return next((q for q in self.questions if q.role == role), None)


def load_survey(path: str) -> Survey:
    """Load and validate a survey from a JSON file."""
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    return parse_survey(raw)


def parse_survey(raw: dict[str, Any]) -> Survey:
    if "title" not in raw or "questions" not in raw:
        raise ValueError("Survey JSON must have 'title' and 'questions'.")

    questions: list[Question] = []
    for item in raw["questions"]:
        scale = item.get("scale")
        questions.append(
            Question(
                id=item["id"],
                text=item["text"],
                type=item["type"],
                role=item.get("role"),
                scale=tuple(scale) if scale else None,
                options=item.get("options"),
            )
        )

    return Survey(
        title=raw["title"],
        description=raw.get("description", ""),
        questions=questions,
        meta=raw.get("meta", {}),
    )
