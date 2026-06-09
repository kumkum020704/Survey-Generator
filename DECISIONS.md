# Design Decisions & Rationale

This document records every meaningful decision made while building the
Synthetic Survey Response Generator, and *why* each one was chosen over these
alternatives. It is the "engineering reasoning" companion to `WRITEUP.md`.

---

## 1. Core modelling approach

### Decision: a causal latent-trait persona model (not independent sampling, not a naive LLM prompt)

**Why.** The brief asks for two things that fight each other:

- *Plausible* = the per-question distributions look real (skewed-positive CSAT,
  fat-tailed NPS).
- *Coherent* = answers within one response don't contradict each other.

| Alternative considered | Why rejected |
|---|---|
| **Independent random sampling per question** | Nails the marginals but produces incoherent rows — e.g. 5/5 satisfaction next to "delivery was a week late". No mechanism links answers. |
| **One naive LLM prompt** ("write a survey response") | Locally fluent but statistically lumpy across 200 rows, hard to control distributions, costs money, non-deterministic, and the brief explicitly says a single naive prompt is not enough. |
| **Causal latent-trait persona model (chosen)** | A shared hidden cause makes coherence a *structural guarantee* while persona weights give realistic marginals. Deterministic, free, controllable. |

**The mechanism:** each respondent gets a hidden satisfaction trait; every
visible answer is a noisy *read* of that same trait through an explicit causal
graph (`delivery → satisfaction → {rating, NPS} → open-text themes`). Because
answers share a cause, they cannot drift into contradiction — yet per-answer
noise still allows natural variation.

---

## 2. Population = a mixture of personas, not one bell curve

### Decision: 5 weighted persona segments (delighted_loyalist → detractor)

**Why.** Real customer populations are a *mixture* of types. A single Gaussian
gives a symmetric blob; real CSAT is skewed (a large happy majority + a vocal
unhappy tail). Modelling segments reproduces that shape and, as a bonus, makes
the model interpretable and tunable — I can describe the retailer's health by
editing five rows in `personas.py`.

**Why these five and these weights.** Tuned to a typical post-purchase
e-commerce profile: ~68% satisfied-or-better, a ~16% neutral middle, a ~16%
unhappy minority. Across the population this yields CSAT ≈ 3.7 and NPS ≈ +6 — a
realistic "healthy but improvable" retailer rather than an implausibly perfect
or implausibly broken one. (A single 200-row sample varies with the seed; the
README demo uses `--seed 47`, a representative draw near this mean.)

---

## 3. Coherence via an explicit causal graph

### Decision: model causal direction `delivery → satisfaction → rating/NPS → open-text`

**Why.** I wanted coherence to be *caused*, not *hoped for*. Concretely:

- A **late delivery** lowers the latent satisfaction (−0.20), which then lowers
  the rating *and* the NPS *and* raises the chance the comment mentions slow
  shipping. One root cause, consistent downstream effects.
- **NPS carries its own bias** on top of satisfaction (loyalists evangelise,
  pragmatists rarely recommend even when content). This keeps NPS and CSAT
  correlated (~0.88) without making one a deterministic copy of the other —
  which would itself be unrealistic.

**Rejected alternative:** deriving NPS as a fixed formula of the rating. That
gives correlation 1.0, which never happens in real data and screams "synthetic".

---

## 4. Open-text generation strategy

### Decision: a theme-conditioned template engine, with an *optional* LLM layer on top

**Why a template engine as the default.** It is free, deterministic, fast, and
— crucially — its output is driven by the *same* hidden state as the numbers,
so the prose can never contradict the ratings. Themes are weighted by the actual
experience: a late delivery makes a delivery complaint likely; the purchased
category surfaces category-specific themes (sizing for Clothing, packaging for
Home); happy customers frequently leave it blank or write a one-liner — exactly
as they do in real surveys.

**Why an LLM layer is offered but off by default.**

| Option | Trade-off |
|---|---|
| LLM always on | Better prose variety, but costs money, non-deterministic, and could break coherence if it free-writes. |
| LLM never | Free and safe, but prose is more templated. |
| **LLM optional, rewrites open-text only, grounded in the structured answers (chosen)** | Best of both: coherence stays owned by the statistical model; the LLM only *expresses* it. Defaults off so the deliverable runs free; `--llm` enables it. |

This also satisfies the brief's "more than a single naive prompt": the LLM mode
conditions on persona + prior answers, controls voice/length via a system
prompt, and batches requests to stay under budget. It is hardened for real APIs:
transient server errors (503/timeout) retry with exponential back-off; a hard
quota/429 is *not* retried but aborts the pass early to protect the free-tier
budget; each returned answer is sanitised and length-checked (junk or
prompt-echo is rejected); and any batch that still fails falls back to template
text. Crucially it **reports** what happened (`[llm] X/10 batches succeeded …`)
so a degraded run can never masquerade as a clean LLM run.

**Provider choice: Gemini by default, Claude optional.** The LLM layer is split
into a shared, provider-agnostic core (prompt construction, per-respondent
conditioning, the JSON contract, the fallback) and a thin per-provider caller.
The default is **Google Gemini `gemini-2.5-flash-lite`** because it is built for
high-volume short text and carries the most generous free-tier quota, so a
200-row run stays at zero cost and is least likely to hit a rate limit.
**Anthropic Claude (Haiku)** is a
one-flag alternative (`--llm-provider claude`). Because only the API call
differs, both providers produce identically-conditioned output and neither can
touch the coherent numeric core — switching providers never changes the
coherence guarantees.

---

## 5. Realistic imperfections (deliberately added)

### Decision: model non-responses and tone variation, don't make the data "too clean"

**Why.** Perfectly-filled, perfectly-aligned data looks synthetic. So:

- **Open-text skip behaviour** — happy, low-verbosity respondents often leave
  the field blank or write "N/A"; unhappy, verbose ones almost always write
  (and write more). Demo response rate ≈ 73%, matching real surveys.
- **Rating/text tone is loosely coupled, not identical** — measurement noise
  means a respondent can rate 4 while writing a mild suggestion, just like
  real people whose number and words don't perfectly match.

---

## 6. Generic schema with optional semantic "roles"

### Decision: questions have a `type` (how to answer) and an optional `role` (what it means)

**Why.** I didn't want a one-trick demo hard-wired to this survey. The engine
uses `role` (`satisfaction`, `nps`, `category`, `delivery_on_time`,
`open_feedback`) to wire questions into the causal model. Questions with an
*unrecognised* role fall back to plausible, type-appropriate sampling — so any
arbitrary survey still produces sensible output and the generator never crashes
on an unfamiliar question. (Tested: `test_generic_survey_without_roles`.)

---

## 7. Validation is a first-class deliverable

### Decision: ship a metrics module that uses only the *public* answers

**Why.** "Plausible and coherent" is only a claim until it's measured. The
validator computes plausibility (distributions), coherence (correlations,
a hard-contradiction scan, complaint targeting), and diversity. Critically it
reads **only the visible answers, never the hidden latent state**, so the exact
same checks would run on real survey data — it is a genuine quality gate, not a
self-fulfilling one. This directly backs the write-up's "how I'd measure"
section and is enforced by the test suite.

---

## 8. Engineering choices

| Decision | Why |
|---|---|
| **Python, standard library only** | Runs anywhere with zero install; no dependency risk for a reviewer. The optional LLM path is the only thing that needs a package, and it's guarded. |
| **Seeded RNG (`--seed`)** | Reproducibility — the same seed gives identical output, which makes the demo and the tests deterministic. (Tested both ways.) |
| **CSV *and* JSON output** | CSV for spreadsheets/quick inspection; JSON for programmatic use and to carry survey metadata. |
| **Diagnostic fields prefixed `_` and kept out of the CSV** | `_persona`/`_latent_satisfaction` are useful for inspection but are not "answers", so they're excluded from the deliverable table. |
| **Statistical tests, not snapshot tests** | The output is random, so tests assert *properties* (skew, correlation > 0.6, contradiction rate < 3%, complaint targeting = 100%) rather than exact strings. |
| **Cheap/fast model for the LLM mode (Gemini 2.5 Flash-Lite by default, Claude Haiku optional)** | Short prose doesn't need a frontier model; Gemini's free tier keeps a 200-row run at zero cost, well inside the < $2 budget. |

---

## 9. Bugs found during development and how they were resolved

| Issue | Decision |
|---|---|
| First coherence metric counted any open-text containing "shipping"/"arrived" as a delivery mention — it conflated delivery *praise* and "shipping fee" grumbles with late-delivery *complaints*, diluting the signal to ~55%. | **Sharpened the metric** to detect lateness complaints specifically (phrases like "later than", "days after", "delayed"). These fragments are only ever assigned to late deliveries, so the metric is now a clean 100% coherence check. |
| Initial tuning produced NPS ≈ −14 with a 16% spike at exactly 0 — too pessimistic and visibly artificial. | **Re-tuned segment priors** (lifted the satisfied tiers, softened detractor/delivery penalties) to NPS ≈ +6, a realistic profile. |
| Printing the validation report crashed on the legacy Windows console (cp1252) because of the `█` bar characters and em-dashes. | **Forced stdout to UTF-8** with `errors="replace"` in both CLIs; files were already written as UTF-8. |
