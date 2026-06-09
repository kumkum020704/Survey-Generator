# Validation report — E-commerce Customer Satisfaction

Generated responses: **200**

## 1. Plausibility — marginal distributions

**Satisfaction (1–5)** — mean 3.74

```
           1 | ███ 17 (8%)
           2 | ████ 18 (9%)
           3 | ██████ 30 (15%)
           4 | ██████████████ 70 (35%)
           5 | █████████████ 65 (32%)
```

**Likelihood to recommend (0–10)** — mean 6.76, NPS score **6.5**

```
           0 | █████ 23 (12%)
           1 | █ 6 (3%)
           2 | █ 3 (2%)
           3 | ██ 8 (4%)
           4 | ██ 11 (6%)
           5 | █ 7 (4%)
           6 | ███ 13 (6%)
           7 | ████ 20 (10%)
           8 | █████ 25 (12%)
           9 | ████ 20 (10%)
          10 | █████████████ 64 (32%)
```

**Category purchased**

```
    Clothing | ██████████ 52 (26%)
       Other | █████ 26 (13%)
 Electronics | █████████████ 64 (32%)
        Home | ████████████ 58 (29%)
```

**Delivery on time**

```
         Yes | █████████████████████████████████ 167 (84%)
          No | ███████ 33 (16%)
```

## 2. Coherence

- Correlation(satisfaction, NPS): **0.891** (expected strongly positive)
- Mean satisfaction — on-time: **4.05** vs late: **2.15** (on-time should be higher)
- Hard self-contradictions (e.g. 5/5 satisfaction + NPS ≤ 3): **0** (0.00% of rows)
- Of open-text comments that complain about a *late* delivery (3 comments), share who actually had a late delivery: **100.0%** (should be ~100%)

## 3. Open-text diversity

- Response rate (non-blank): **73.0%**
- Unique-text ratio among answers: **95.2%**
