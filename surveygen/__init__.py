"""Synthetic survey response generator.

A small, dependency-free toolkit that turns a declarative survey definition
into N realistic and internally-coherent synthetic responses.

The core idea is a *causal latent-trait persona model* (see engine.py): each
respondent is drawn from a persona segment, given a hidden satisfaction trait,
and every visible answer is sampled conditioned on that trait so the answers
cannot contradict one another.
"""

from .schema import Survey, Question, load_survey
from .engine import ResponseGenerator
from .validate import validate

__all__ = [
    "Survey",
    "Question",
    "load_survey",
    "ResponseGenerator",
    "validate",
]

__version__ = "1.0.0"
