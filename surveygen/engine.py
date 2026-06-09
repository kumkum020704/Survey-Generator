"""The generative engine: a causal latent-trait model.

Coherence is the hard part of this assignment. A respondent who rates overall
satisfaction 5/5 should not, in the same breath, give an NPS of 1 or write an
angry comment about late delivery. We get this for free by sampling answers
from a shared hidden cause rather than independently.

Causal graph (arrows = "influences"):

    persona segment ─┐
    category ────────┼──► delivery_on_time ─┐
                     │                       ├──► satisfaction_latent ──► rating
                     └───────────────────────┘            │             └─► NPS
                                                           └──► open-text themes

Everything downstream of ``satisfaction_latent`` is a noisy *read* of the same
underlying disposition, so contradictions are structurally unlikely while still
allowing realistic individual variation (a happy customer can still tick "4"
and occasionally a delighted one had a late parcel).

For questions whose ``role`` the engine does not recognise it falls back to
plausible independent sampling, so arbitrary surveys still work.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from .schema import Question, Survey
from .personas import Segment, pick_segment
from .opentext import OpenTextWriter

# Phrases that belong only in positive responses. Using them alongside a low
# satisfaction score, a low NPS, or a late delivery is a self-contradiction.
_POSITIVE_STARTERS = (
    "pretty much perfect",
    "loved it",
    "no real complaints",
    "very smooth from start to finish",
    "really happy with",
    "great service overall",
    "honestly, nothing major",
)
_POSITIVE_VERBATIM = frozenset({"nothing", "all good", "nothing to add"})


def _text_is_positive(text: str) -> bool:
    t = text.strip().lower()
    if t in _POSITIVE_VERBATIM:
        return True
    return any(t.startswith(p) for p in _POSITIVE_STARTERS)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


# Category mix and per-category delivery risk (bulky/Home & Electronics parcels
# are a little more likely to be late). Kept mild so it is a nudge, not a rule.
CATEGORY_WEIGHTS = {
    "Electronics": 0.30,
    "Clothing": 0.30,
    "Home": 0.25,
    "Other": 0.15,
}
CATEGORY_LATE_MODIFIER = {
    "Electronics": 0.04,
    "Clothing": 0.00,
    "Home": 0.06,
    "Other": 0.02,
}


@dataclass
class Respondent:
    """The hidden state of one synthetic person plus their visible answers."""

    segment: Segment
    latent_satisfaction: float
    category: str
    delivery_on_time: bool
    answers: dict[str, Any] = field(default_factory=dict)


class ResponseGenerator:
    def __init__(self, survey: Survey, seed: int | None = None):
        self.survey = survey
        self.rng = random.Random(seed)
        self.opentext = OpenTextWriter(self.rng)

        # Resolve the demo roles once so generation is cheap per respondent.
        self._q_satisfaction = survey.by_role("satisfaction")
        self._q_nps = survey.by_role("nps")
        self._q_category = survey.by_role("category")
        self._q_delivery = survey.by_role("delivery_on_time")
        self._q_feedback = survey.by_role("open_feedback")

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def generate(self, n: int) -> list[dict[str, Any]]:
        return [self._one(i) for i in range(n)]

    # ------------------------------------------------------------------ #
    # One respondent
    # ------------------------------------------------------------------ #
    def _one(self, index: int) -> dict[str, Any]:
        person = self._draw_hidden_state()
        answers: dict[str, Any] = {}

        for q in self.survey.questions:
            answers[q.id] = self._answer(q, person)

        answers = self._coherence_pass(answers, person)

        person.answers = answers
        return {
            "respondent_id": f"R{index + 1:04d}",
            "_persona": person.segment.name,           # diagnostics, prefixed "_"
            "_latent_satisfaction": round(person.latent_satisfaction, 3),
            **answers,
        }

    # ------------------------------------------------------------------ #
    # Coherence pass
    # ------------------------------------------------------------------ #
    def _coherence_pass(self, answers: dict[str, Any], person: Respondent) -> dict[str, Any]:
        """Regenerate open-text that contradicts the row's structured answers.

        Runs after all questions are answered so the visible sat / NPS / delivery
        values are known. Rewrites only when a positive phrase appears alongside
        a low rating (≤ 2), a low NPS (≤ 3), or a late delivery.
        """
        q_txt = self._q_feedback
        if q_txt is None:
            return answers

        text = str(answers.get(q_txt.id, ""))
        if not _text_is_positive(text):
            return answers  # fast path: no contradiction

        sat_val = answers.get(self._q_satisfaction.id) if self._q_satisfaction else None
        nps_val = answers.get(self._q_nps.id) if self._q_nps else None
        on_time = (
            str(answers.get(self._q_delivery.id, "Yes")).strip().lower()
            in ("yes", "y", "true", "1")
        ) if self._q_delivery else True

        needs_negative = (not on_time) or (sat_val is not None and sat_val <= 2)
        needs_non_positive = nps_val is not None and nps_val <= 3

        cat = person.category.lower()
        if needs_negative:
            answers[q_txt.id] = self.opentext._negative(person, cat)
        elif needs_non_positive:
            answers[q_txt.id] = self.opentext._mixed(person, cat)

        return answers

    def _draw_hidden_state(self) -> Respondent:
        rng = self.rng
        seg = pick_segment(rng)

        # 1. Category is an upstream driver (what they bought).
        category = self._sample_category()

        # 2. Delivery timeliness: segment prior, nudged by category risk.
        late_modifier = CATEGORY_LATE_MODIFIER.get(category, 0.0)
        p_ontime = _clamp(seg.ontime_prior - late_modifier, 0.02, 0.99)
        on_time = rng.random() < p_ontime

        # 3. Latent satisfaction: segment trait, penalised by a late delivery.
        latent = rng.gauss(seg.base_sat, seg.sd)
        if not on_time:
            latent -= 0.20  # a missed delivery genuinely sours the experience
        latent = _clamp(latent, 0.0, 1.0)

        return Respondent(
            segment=seg,
            latent_satisfaction=latent,
            category=category,
            delivery_on_time=on_time,
        )

    # ------------------------------------------------------------------ #
    # Per-question answering
    # ------------------------------------------------------------------ #
    def _answer(self, q: Question, person: Respondent) -> Any:
        role = q.role
        if role == "satisfaction":
            return self._rating_from_latent(q, person.latent_satisfaction)
        if role == "nps":
            return self._nps_from_latent(q, person)
        if role == "category":
            return person.category
        if role == "delivery_on_time":
            return self._yesno(q, person.delivery_on_time)
        if role == "open_feedback":
            return self.opentext.write(person, self.survey)

        # Unknown role -> generic, type-appropriate sampling.
        return self._generic_answer(q, person)

    def _sample_category(self) -> str:
        opts = self._q_category.options if self._q_category else list(CATEGORY_WEIGHTS)
        weights = [CATEGORY_WEIGHTS.get(o, 1.0 / len(opts)) for o in opts]
        return self.rng.choices(opts, weights=weights, k=1)[0]

    def _rating_from_latent(self, q: Question, latent: float) -> int:
        lo, hi = q.scale
        span = hi - lo
        # Map latent (0..1) onto the scale, add measurement noise, then round.
        score = lo + latent * span + self.rng.gauss(0, 0.45)
        return int(round(_clamp(score, lo, hi)))

    def _nps_from_latent(self, q: Question, person: Respondent) -> int:
        lo, hi = q.scale  # typically 0..10
        span = hi - lo
        score = lo + person.latent_satisfaction * span
        score += person.segment.nps_bias            # loyalty / evangelism effect
        if not person.delivery_on_time:
            score -= 1.2                             # extra recommend penalty
        score += self.rng.gauss(0, 0.9)             # individual noise
        return int(round(_clamp(score, lo, hi)))

    def _yesno(self, q: Question, value: bool) -> str:
        opts = q.options or ["Yes", "No"]
        yes = next((o for o in opts if o.strip().lower() in ("yes", "y", "true")), opts[0])
        no = next((o for o in opts if o.strip().lower() in ("no", "n", "false")), opts[-1])
        return yes if value else no

    def _generic_answer(self, q: Question, person: Respondent) -> Any:
        """Fallback for questions without a recognised role."""
        if q.type in ("rating", "nps"):
            # Re-use the shared trait so even generic numerics stay coherent.
            return self._rating_from_latent(q, person.latent_satisfaction)
        if q.type == "single_choice":
            return self.rng.choice(q.options)
        if q.type == "open_text":
            return self.opentext.write(person, self.survey)
        return None
