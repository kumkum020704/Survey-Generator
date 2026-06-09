"""Persona segments.

Real survey populations are a *mixture* of customer types, not a single bell
curve. Modelling that mixture is what gives the output a realistic, slightly
skewed shape (most people are happy, a long unhappy tail) instead of a flat or
naively-uniform distribution.

Each segment carries the priors that drive an individual's hidden state:

  weight        share of the population
  base_sat      mean of the latent satisfaction trait (0..1)
  sd            spread of that trait within the segment
  nps_bias      how much more/less likely they are to actively recommend,
                independent of raw satisfaction (loyalists evangelise, neutral
                pragmatists rarely do) — measured in NPS points
  ontime_prior  probability their delivery arrived on time
  verbosity     how likely / how much they write in open text
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Segment:
    name: str
    weight: float
    base_sat: float
    sd: float
    nps_bias: float
    ontime_prior: float
    verbosity: float


# Weights sum to 1.0. Tuned to a typical post-purchase e-commerce CSAT shape:
# a large satisfied majority, a meaningful neutral middle, and a vocal unhappy
# minority that drags NPS down.
SEGMENTS: list[Segment] = [
    Segment("delighted_loyalist",  weight=0.38, base_sat=0.93, sd=0.06, nps_bias=+1.0, ontime_prior=0.95, verbosity=0.45),
    Segment("satisfied_regular",   weight=0.30, base_sat=0.78, sd=0.09, nps_bias=+0.4, ontime_prior=0.90, verbosity=0.40),
    Segment("neutral_pragmatist",  weight=0.16, base_sat=0.58, sd=0.10, nps_bias=-0.7, ontime_prior=0.85, verbosity=0.30),
    Segment("frustrated_shopper",  weight=0.10, base_sat=0.33, sd=0.10, nps_bias=-1.5, ontime_prior=0.66, verbosity=0.70),
    Segment("detractor",           weight=0.06, base_sat=0.15, sd=0.08, nps_bias=-2.2, ontime_prior=0.48, verbosity=0.82),
]


def pick_segment(rng) -> Segment:
    """Sample a persona segment proportional to its population weight."""
    r = rng.random()
    cumulative = 0.0
    for seg in SEGMENTS:
        cumulative += seg.weight
        if r <= cumulative:
            return seg
    return SEGMENTS[-1]  # floating-point guard
