"""Tests for the synthetic survey generator.

Run with:  python -m pytest test_surveygen.py   (or)   python test_surveygen.py

The tests assert the two properties the brief cares about — plausibility and
coherence — as statistical guarantees over a sample, plus reproducibility and
schema handling. They use only the stdlib so they run anywhere.
"""

from __future__ import annotations

import statistics

from surveygen import load_survey, ResponseGenerator
from surveygen.schema import parse_survey
from surveygen.validate import validate


DEMO = {
    "title": "E-commerce Customer Satisfaction",
    "questions": [
        {"id": "q1", "text": "Overall satisfaction?", "type": "rating", "scale": [1, 5], "role": "satisfaction"},
        {"id": "q2", "text": "Recommend?", "type": "nps", "scale": [0, 10], "role": "nps"},
        {"id": "q3", "text": "Category?", "type": "single_choice",
         "options": ["Electronics", "Clothing", "Home", "Other"], "role": "category"},
        {"id": "q4", "text": "Delivery on time?", "type": "single_choice",
         "options": ["Yes", "No"], "role": "delivery_on_time"},
        {"id": "q5", "text": "Improve?", "type": "open_text", "role": "open_feedback"},
    ],
}


def _gen(n=400, seed=1):
    survey = parse_survey(DEMO)
    return survey, ResponseGenerator(survey, seed=seed).generate(n)


def test_count_and_fields():
    survey, rows = _gen(200)
    assert len(rows) == 200
    for r in rows:
        for q in survey.questions:
            assert q.id in r


def test_values_in_range():
    survey, rows = _gen()
    for r in rows:
        assert 1 <= r["q1"] <= 5
        assert 0 <= r["q2"] <= 10
        assert r["q3"] in {"Electronics", "Clothing", "Home", "Other"}
        assert r["q4"] in {"Yes", "No"}
        assert isinstance(r["q5"], str)


def test_reproducible_with_seed():
    s1, r1 = _gen(100, seed=7)
    s2, r2 = _gen(100, seed=7)
    assert r1 == r2


def test_different_seeds_differ():
    _, r1 = _gen(100, seed=1)
    _, r2 = _gen(100, seed=2)
    assert r1 != r2


def test_distribution_is_skewed_positive():
    # E-commerce CSAT should lean satisfied, not be uniform.
    _, rows = _gen()
    mean_sat = statistics.fmean(r["q1"] for r in rows)
    assert mean_sat > 3.3, mean_sat


def test_satisfaction_and_nps_correlate():
    survey, rows = _gen()
    rep = validate(survey, rows)
    assert rep["coherence"]["corr_satisfaction_nps"] > 0.6


def test_late_delivery_lowers_satisfaction():
    survey, rows = _gen()
    rep = validate(survey, rows)
    on = rep["coherence"]["mean_satisfaction_on_time"]
    late = rep["coherence"]["mean_satisfaction_late"]
    assert on > late


def test_few_hard_contradictions():
    survey, rows = _gen()
    rep = validate(survey, rows)
    assert rep["coherence"]["hard_contradiction_rate"] < 0.03


def test_late_delivery_complaints_are_targeted():
    # Anyone who complains their delivery was late should actually have had a
    # late delivery — this is the sharpest coherence guarantee.
    survey, rows = _gen()
    rep = validate(survey, rows)
    assert rep["coherence"]["late_complaints_actually_late"] == 1.0


def test_open_text_is_diverse():
    survey, rows = _gen()
    rep = validate(survey, rows)
    assert rep["diversity"]["open_text_unique_ratio"] > 0.5


def test_generic_survey_without_roles():
    # A survey with no roles should still produce valid, in-range answers.
    raw = {
        "title": "Generic",
        "questions": [
            {"id": "a", "text": "Rate", "type": "rating", "scale": [1, 5]},
            {"id": "b", "text": "Pick", "type": "single_choice", "options": ["X", "Y", "Z"]},
            {"id": "c", "text": "Say", "type": "open_text"},
        ],
    }
    survey = parse_survey(raw)
    rows = ResponseGenerator(survey, seed=3).generate(50)
    assert len(rows) == 50
    for r in rows:
        assert 1 <= r["a"] <= 5
        assert r["b"] in {"X", "Y", "Z"}


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  PASS  {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests passed.")


if __name__ == "__main__":
    _run_all()
