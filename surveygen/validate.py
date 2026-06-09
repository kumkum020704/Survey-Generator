"""Validation: does the synthetic data actually look good?

"Plausible and coherent" is only meaningful if we can measure it. This module
computes the metrics that back up that claim and writes a human-readable
report. It checks three things:

  1. PLAUSIBILITY  - are the marginal distributions realistic in shape?
  2. COHERENCE     - do answers within a response agree (correlations + a
                     hard scan for self-contradicting rows)?
  3. DIVERSITY     - is the open text varied rather than copy-pasted?

It deliberately uses only the public answers (not the hidden latent state) so
it would work just as well on real survey data — i.e. it is a genuine quality
gate, not a self-fulfilling check.
"""

from __future__ import annotations

import statistics
from collections import Counter
from typing import Any

from .schema import Survey


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return float("nan")
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    if dx == 0 or dy == 0:
        return float("nan")
    return num / (dx * dy)


def _histogram(values: list[int], lo: int, hi: int) -> dict[int, int]:
    counts = {v: 0 for v in range(lo, hi + 1)}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    return counts


def _nps_score(scores: list[int]) -> float:
    if not scores:
        return float("nan")
    promoters = sum(1 for s in scores if s >= 9)
    detractors = sum(1 for s in scores if s <= 6)
    return 100.0 * (promoters - detractors) / len(scores)


def validate(survey: Survey, responses: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a structured metrics dict for the generated responses."""
    n = len(responses)
    q_sat = survey.by_role("satisfaction")
    q_nps = survey.by_role("nps")
    q_cat = survey.by_role("category")
    q_del = survey.by_role("delivery_on_time")
    q_txt = survey.by_role("open_feedback")

    report: dict[str, Any] = {"n": n, "distributions": {}, "coherence": {}, "diversity": {}}

    # ---- Distributions ----------------------------------------------------
    if q_sat:
        vals = [r[q_sat.id] for r in responses]
        lo, hi = q_sat.scale
        report["distributions"]["satisfaction"] = {
            "mean": round(statistics.fmean(vals), 2),
            "histogram": _histogram(vals, lo, hi),
        }
    if q_nps:
        vals = [r[q_nps.id] for r in responses]
        report["distributions"]["nps"] = {
            "mean": round(statistics.fmean(vals), 2),
            "nps_score": round(_nps_score(vals), 1),
            "histogram": _histogram(vals, *q_nps.scale),
        }
    if q_cat:
        report["distributions"]["category"] = dict(
            Counter(r[q_cat.id] for r in responses)
        )
    if q_del:
        report["distributions"]["delivery_on_time"] = dict(
            Counter(r[q_del.id] for r in responses)
        )

    # ---- Coherence --------------------------------------------------------
    if q_sat and q_nps:
        sat = [r[q_sat.id] for r in responses]
        nps = [r[q_nps.id] for r in responses]
        report["coherence"]["corr_satisfaction_nps"] = round(_pearson(sat, nps), 3)

    if q_sat and q_del:
        on_vals = [r[q_sat.id] for r in responses if _is_yes(r[q_del.id])]
        late_vals = [r[q_sat.id] for r in responses if not _is_yes(r[q_del.id])]
        report["coherence"]["mean_satisfaction_on_time"] = (
            round(statistics.fmean(on_vals), 2) if on_vals else None
        )
        report["coherence"]["mean_satisfaction_late"] = (
            round(statistics.fmean(late_vals), 2) if late_vals else None
        )

    # Hard contradiction scan: top-box satisfaction with detractor NPS, or
    # bottom-box satisfaction with promoter NPS. Real data has a tiny amount of
    # this; a flood of it would mean the model is incoherent.
    if q_sat and q_nps:
        slo, shi = q_sat.scale
        contradictions = 0
        for r in responses:
            s, p = r[q_sat.id], r[q_nps.id]
            if s == shi and p <= 3:
                contradictions += 1
            elif s == slo and p >= 9:
                contradictions += 1
        report["coherence"]["hard_contradictions"] = contradictions
        report["coherence"]["hard_contradiction_rate"] = round(contradictions / n, 4)

    # Delivery-complaint targeting: of the people who complain in open text that
    # their delivery was *late*, how many actually had a late delivery? This is
    # a sharp coherence test — a complaint about lateness from someone whose
    # delivery was on time would be a self-contradiction.
    if q_txt and q_del:
        complaints = [
            r for r in responses
            if _complains_late_delivery(str(r.get(q_txt.id, "")))
        ]
        if complaints:
            correct = sum(1 for r in complaints if not _is_yes(r[q_del.id]))
            report["coherence"]["late_delivery_complaints"] = len(complaints)
            report["coherence"]["late_complaints_actually_late"] = round(
                correct / len(complaints), 3
            )

    # ---- Diversity --------------------------------------------------------
    if q_txt:
        texts = [str(r.get(q_txt.id, "")).strip() for r in responses]
        nonblank = [t for t in texts if t and t not in ("N/A", "-", "Nothing")]
        report["diversity"]["open_text_response_rate"] = round(
            len(nonblank) / n, 3
        )
        report["diversity"]["open_text_unique_ratio"] = (
            round(len(set(nonblank)) / len(nonblank), 3) if nonblank else 0.0
        )

    return report


def _is_yes(value: Any) -> bool:
    return str(value).strip().lower() in ("yes", "y", "true", "1")


def _complains_late_delivery(text: str) -> bool:
    """Detect a complaint specifically about a *late* delivery (not praise,
    not a generic shipping-fee grumble)."""
    t = text.lower()
    phrases = (
        "later than", "longer than", "days after", "delayed", "delay",
        "took far longer", "showed up days", "arrived later",
    )
    return any(p in t for p in phrases)


def format_report(survey: Survey, report: dict[str, Any]) -> str:
    """Render the metrics dict as a Markdown report."""
    out: list[str] = []
    out.append(f"# Validation report — {survey.title}")
    out.append(f"\nGenerated responses: **{report['n']}**\n")

    d = report["distributions"]
    out.append("## 1. Plausibility — marginal distributions\n")
    if "satisfaction" in d:
        s = d["satisfaction"]
        out.append(f"**Satisfaction (1–5)** — mean {s['mean']}")
        out.append(_bar_chart(s["histogram"]))
    if "nps" in d:
        s = d["nps"]
        out.append(
            f"\n**Likelihood to recommend (0–10)** — mean {s['mean']}, "
            f"NPS score **{s['nps_score']}**"
        )
        out.append(_bar_chart(s["histogram"]))
    if "category" in d:
        out.append("\n**Category purchased**")
        out.append(_bar_chart(d["category"]))
    if "delivery_on_time" in d:
        out.append("\n**Delivery on time**")
        out.append(_bar_chart(d["delivery_on_time"]))

    c = report["coherence"]
    out.append("\n## 2. Coherence\n")
    if "corr_satisfaction_nps" in c:
        out.append(
            f"- Correlation(satisfaction, NPS): **{c['corr_satisfaction_nps']}** "
            f"(expected strongly positive)"
        )
    if "mean_satisfaction_on_time" in c:
        out.append(
            f"- Mean satisfaction — on-time: **{c['mean_satisfaction_on_time']}** "
            f"vs late: **{c['mean_satisfaction_late']}** "
            f"(on-time should be higher)"
        )
    if "hard_contradictions" in c:
        out.append(
            f"- Hard self-contradictions (e.g. 5/5 satisfaction + NPS ≤ 3): "
            f"**{c['hard_contradictions']}** "
            f"({c['hard_contradiction_rate'] * 100:.2f}% of rows)"
        )
    if "late_complaints_actually_late" in c:
        out.append(
            f"- Of open-text comments that complain about a *late* delivery "
            f"({c['late_delivery_complaints']} comments), share who actually "
            f"had a late delivery: **{c['late_complaints_actually_late'] * 100:.1f}%** "
            f"(should be ~100%)"
        )

    v = report["diversity"]
    out.append("\n## 3. Open-text diversity\n")
    if "open_text_response_rate" in v:
        out.append(f"- Response rate (non-blank): **{v['open_text_response_rate'] * 100:.1f}%**")
        out.append(f"- Unique-text ratio among answers: **{v['open_text_unique_ratio'] * 100:.1f}%**")

    out.append("")
    return "\n".join(out)


def _bar_chart(counts: dict[Any, int]) -> str:
    if not counts:
        return ""
    total = sum(counts.values()) or 1
    width = 40
    lines = ["", "```"]
    for key, val in counts.items():
        bar = "█" * round(width * val / total)
        lines.append(f"{str(key):>12} | {bar} {val} ({100 * val / total:.0f}%)")
    lines.append("```")
    return "\n".join(lines)
