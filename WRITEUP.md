# Synthetic Survey Response Generator — Write-up

## Approach, and why I chose it

The two qualities the brief asks for — **plausible** and **coherent** — pull in
slightly different directions. Plausibility is about the *marginal* shape of
each question (most e-commerce customers are satisfied, NPS has a fat promoter
tail and a vocal detractor spike). Coherence is about the *joint* shape: one
person's answers must hang together. A generator that samples each question
independently nails the marginals but produces incoherent rows (5/5 satisfaction
next to an angry "delivery was a week late" comment). A single naive LLM prompt
("write a survey response") tends to do the opposite — locally fluent but
statistically lumpy and hard to control across 200 rows.

I chose a **causal latent-trait persona model** because it gets both at once:

1. **A population mixture, not one bell curve.** Each respondent is drawn from
   one of five persona segments (delighted loyalist → detractor) with realistic
   population weights. This reproduces the characteristic skewed CSAT/NPS shape
   instead of a flat or Gaussian blob.
2. **A shared hidden cause.** Each respondent gets a latent satisfaction trait
   plus upstream drivers (purchase category, whether delivery was on time).
   Every visible answer — rating, NPS, open-text — is a *noisy read of that same
   trait*. Because they share a cause, they can't drift into contradiction, yet
   individual noise still allows natural variation (a happy customer can tick 4,
   a delighted one can occasionally have had a late parcel).
3. **An explicit causal graph.** `delivery_on_time → satisfaction → {rating,
   NPS} → open-text themes`. A late delivery mechanically lowers satisfaction,
   which lowers the rating and NPS, and raises the probability the comment
   mentions slow shipping. Coherence is a structural property, not something I
   hope the sampler stumbles into.
4. **Open text conditioned on state.** Comments are assembled from
   theme-tagged fragments weighted by the respondent's actual experience
   (late delivery → delivery complaint; category → category-specific themes;
   high satisfaction → brief praise or a blank, exactly as real surveys behave).

This is deterministic (seeded), free, dependency-free, fast, and fully
controllable — I can dial the retailer's health by editing five segment rows.
I added an **optional** LLM mode that rewrites *only* the open-text field,
grounded in the already-decided structured answers. That keeps the coherent
numeric core owned by the statistical model and uses the LLM purely for prose
variety — and it's "more than a naive prompt" (persona + prior-answer
conditioning, voice/length control, batching, output sanitisation, retries with
a budget-safe back-off, and an honest fallback that reports whenever it degrades
to template text). It stays off by default so the deliverable runs at zero cost.

## Why this hybrid split

**Structured fields stay rule-based.** Satisfaction, NPS, category and delivery
are tied together by the causal model — coherence is a structural guarantee, not
something an LLM could reliably enforce across 200 rows. It also means the core
run needs no API key, budget or network.

**Only open-text uses the LLM.** Free text carries no numerical constraint to
violate, so rewriting it — strictly conditioned on the already-decided rating,
NPS, category and delivery — adds linguistic variety without ever touching the
coherent numeric core. If no key is present the run automatically keeps the
template text.

## How I'd measure whether the outputs are any good

`validate.py` / `analyze.py` compute this automatically; the tests assert it.
I measure three things, using **only the public answers** (never the hidden
latent state) so the same checks would work on real survey data — they're a
genuine quality gate, not a self-fulfilling one.

- **Plausibility (marginals).** Distribution shape and summary stats per
  question: CSAT mean and histogram, NPS score (% promoters − % detractors),
  category mix, on-time rate. I sanity-check these against published
  e-commerce benchmarks (CSAT mode at 4–5, on-time ~80–90%, NPS neutral-to-
  positive). On the seeded demo run: CSAT mean ≈ 3.7 (mode 4), ~84% on-time, and
  NPS ≈ +6 — a healthy-but-improvable retailer, all in the realistic band.
- **Coherence (joint).** (a) Pearson correlation between satisfaction and NPS
  (~0.88 — strongly positive, as expected); (b) mean satisfaction for on-time
  vs late deliveries (≈4.05 vs ≈2.15 — late is clearly worse); (c) a **hard
  contradiction scan** counting rows like 5/5 satisfaction + NPS ≤ 3 (0% on the
  demo run); (d) **complaint targeting** — 100% of comments complaining about a
  *late* delivery come from respondents who actually had one.
- **Diversity.** Open-text response rate (~70–75%, matching real skip
  behaviour) and unique-text ratio — ~61% from the free template engine, rising
  to ~95% with the optional LLM pass — to confirm the free text isn't
  copy-pasted.

If I had labelled real responses, the strongest test is a **discriminator**:
train a simple classifier (or have a human) try to tell synthetic from real. If
it can't beat chance, the synthetic data is good. I'd also compare
**distributions** (KS test per question) and **cross-question correlation
matrices** between real and synthetic.

## One thing I'd do differently with more time

I'd **fit the persona segments to a small seed of real data** instead of
hand-tuning their priors. With even ~100 real responses I'd estimate the segment
mixture and the causal weights (e.g. via EM / a small latent-class model), so
the marginals and correlations match the real population by construction rather
than by my judgement — and I'd add the discriminator test above to the CI loop
as the headline quality metric, regenerating until a classifier can no longer
separate real from synthetic.
