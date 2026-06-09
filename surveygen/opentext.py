"""Open-text generation conditioned on the respondent's hidden state.

A naive open-text generator picks a random canned sentence and produces output
that contradicts the numbers ("Terrible!" next to a 5/5). Here the comment is
assembled from theme fragments whose selection is driven by the *same* state
that produced the ratings:

  * sentiment (positive / mixed / negative) comes from latent satisfaction,
  * topics are weighted by the actual experience — a late delivery makes a
    delivery complaint likely; the purchased category surfaces category themes,
  * verbose, unhappy personas write more and skip the question less often,
  * happy customers frequently leave it blank or write a one-liner, exactly as
    they do in real surveys.

The result reads like human free text and never fights the structured answers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid a circular import at runtime
    from .engine import Respondent
    from .schema import Survey


# ---------------------------------------------------------------------------
# Fragment banks. {cat} is filled with the purchased category in lower case.
# Multiple phrasings per theme give lexical variety across 200 responses.
# ---------------------------------------------------------------------------

POSITIVE_OPENERS = [
    "Honestly, nothing major",
    "Really happy with the experience",
    "Great service overall",
    "Pretty much perfect",
    "No real complaints",
    "Very smooth from start to finish",
    "Loved it",
]

POSITIVE_SUGGESTIONS = [
    "maybe a few more deals would be nice",
    "perhaps a loyalty program for regulars",
    "keep doing what you're doing",
    "a wider {cat} selection would be a bonus",
    "faster checkout would be a small plus",
    "more colour options on {cat} items",
]

MIXED_OPENERS = [
    "Mostly fine, but",
    "Decent experience overall, though",
    "Good in general, however",
    "It was okay,",
    "No major issues, still",
]

NEGATIVE_OPENERS = [
    "Pretty disappointed",
    "Not a great experience this time",
    "Frustrated, to be honest",
    "Quite let down",
    "Really not impressed",
]

# Topic fragments keyed by theme. The engine picks 1-2 topics by weight.
TOPIC_FRAGMENTS = {
    "delivery_late": [
        "the delivery arrived later than promised",
        "shipping took far longer than the estimate",
        "my order showed up days after the delivery date",
        "the parcel was delayed with no real updates",
    ],
    "delivery_good": [
        "delivery was quick",
        "shipping was right on time",
        "the parcel came earlier than expected",
    ],
    "tracking": [
        "the tracking information was vague and rarely updated",
        "I'd love clearer, more accurate order tracking",
        "real-time tracking would make a big difference",
    ],
    "price": [
        "prices feel a little high compared to competitors",
        "more competitive pricing would help",
        "the shipping fee felt steep",
        "a clearer discount policy would be appreciated",
    ],
    "packaging": [
        "the packaging could be sturdier",
        "my {cat} item arrived in flimsy packaging",
        "less wasteful packaging would be great",
    ],
    "product_quality": [
        "the {cat} item didn't quite match the description",
        "build quality on the {cat} product could be better",
        "the {cat} item felt lower quality than the photos suggested",
    ],
    "sizing": [
        "the sizing on {cat} runs inconsistent",
        "a better size guide for {cat} would help a lot",
    ],
    "returns": [
        "the returns process was more painful than it should be",
        "make returns and refunds simpler and faster",
        "refunds took too long to come through",
    ],
    "support": [
        "customer support was slow to respond",
        "it was hard to reach a human when I had a question",
        "support could be more helpful and responsive",
    ],
    "website": [
        "the website could be easier to navigate",
        "the app felt a bit clunky at checkout",
        "search and filters on the site need work",
    ],
}

# Which themes are plausible for which category (used to weight selection).
CATEGORY_THEMES = {
    "Electronics": ["product_quality", "price", "packaging", "support", "returns"],
    "Clothing": ["sizing", "returns", "product_quality", "price"],
    "Home": ["packaging", "product_quality", "price", "returns"],
    "Other": ["product_quality", "price", "support", "website"],
}

POSITIVE_NONRESPONSES = ["", "", "N/A", "Nothing", "All good", "Nothing to add", "-"]


class OpenTextWriter:
    def __init__(self, rng):
        self.rng = rng

    # ------------------------------------------------------------------ #
    def write(self, person: "Respondent", survey: "Survey") -> str:
        latent = person.latent_satisfaction
        cat = person.category.lower()

        # Decide whether they answer at all. Happy, low-verbosity people often
        # don't; unhappy, verbose people almost always do.
        answer_prob = 0.45 + 0.55 * person.segment.verbosity
        if latent < 0.4:
            answer_prob = min(0.97, answer_prob + 0.25)
        if self.rng.random() > answer_prob:
            # Positive non-responses ("Nothing", "All good") are only plausible
            # when delivery was on time; a late parcel warrants a real answer.
            if latent >= 0.7 and person.delivery_on_time:
                return self.rng.choice(POSITIVE_NONRESPONSES)
            return ""

        # A late delivery always caps the response at mixed or negative.
        # Prevents "Very smooth from start to finish" appearing next to delivery=No.
        if not person.delivery_on_time:
            if latent >= 0.42:
                return self._mixed(person, cat)
            return self._negative(person, cat)

        if latent >= 0.68:
            return self._positive(cat)
        if latent >= 0.42:
            return self._mixed(person, cat)
        return self._negative(person, cat)

    # ------------------------------------------------------------------ #
    def _positive(self, cat: str) -> str:
        opener = self.rng.choice(POSITIVE_OPENERS)
        # Often a bare compliment; sometimes a gentle suggestion.
        if self.rng.random() < 0.55:
            return self._cap(opener) + "."
        suggestion = self.rng.choice(POSITIVE_SUGGESTIONS).format(cat=cat)
        return f"{self._cap(opener)} — {suggestion}."

    def _mixed(self, person: "Respondent", cat: str) -> str:
        opener = self.rng.choice(MIXED_OPENERS)
        topics = self._pick_topics(person, cat, n_min=1, n_max=2)
        body = self._join(topics)
        return f"{opener} {body}."

    def _negative(self, person: "Respondent", cat: str) -> str:
        opener = self.rng.choice(NEGATIVE_OPENERS)
        topics = self._pick_topics(person, cat, n_min=1, n_max=2, negative=True)
        body = self._join(topics)
        return f"{self._cap(opener)} — {body}."

    # ------------------------------------------------------------------ #
    def _pick_topics(self, person, cat, n_min, n_max, negative=False) -> list[str]:
        weights: dict[str, float] = {}

        # Delivery is the strongest, most concrete signal.
        if not person.delivery_on_time:
            weights["delivery_late"] = 3.5
            weights["tracking"] = 1.2
        elif not negative:
            # On-time + already complaining: don't praise delivery.
            weights["delivery_good"] = 0.6

        # Category-appropriate themes.
        for theme in CATEGORY_THEMES.get(person.category, []):
            weights[theme] = weights.get(theme, 0.0) + 1.0

        # Price and support are universal low-level grumbles.
        weights["price"] = weights.get("price", 0.0) + 0.8
        weights["support"] = weights.get("support", 0.0) + 0.4

        themes = list(weights)
        wts = [weights[t] for t in themes]
        k = self.rng.randint(n_min, min(n_max, len(themes)))

        chosen: list[str] = []
        picked_themes: list[str] = []
        for _ in range(k):
            if not themes:
                break
            t = self.rng.choices(themes, weights=wts, k=1)[0]
            idx = themes.index(t)
            themes.pop(idx)
            wts.pop(idx)
            picked_themes.append(t)
            chosen.append(self.rng.choice(TOPIC_FRAGMENTS[t]).format(cat=cat))
        return chosen

    def _join(self, parts: list[str]) -> str:
        parts = [p for p in parts if p]
        if not parts:
            return "a few small things could be smoother"
        if len(parts) == 1:
            return parts[0]
        return parts[0] + ", and " + parts[1]

    @staticmethod
    def _cap(s: str) -> str:
        return s[0].upper() + s[1:] if s else s
