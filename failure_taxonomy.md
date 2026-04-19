# VP Substitution Agent — Failure Taxonomy

**Project:** VP Substitution Agent — LLM Evals
**Model:** claude-opus-4-5 | **Queries tested:** 20 | **Date:** 2026-04-19

---

## Part A — Model Failure Modes

Failures the **model** could make when generating substitution responses.

| ID | Failure Mode | Description | Instances Found | Example |
|----|-------------|-------------|----------------|---------|
| FM-01 | Dietary Constraint Violation | Recommended substitute contains an ingredient that violates the stated restriction (e.g. butter recommended for a dairy-free query) | 0 | — (model performed correctly on all 20 queries) |
| FM-02 | Missing or Incorrect Ratio | Substitution provided without a measurement ratio, or ratio is wrong for the context | 0 | — (all responses included ratios) |
| FM-03 | Wrong Ingredient Role | Bot misidentifies what the original ingredient does in the dish, leading to a functionally incompatible substitute | 0 | — (all Role in dish sections were accurate) |
| FM-04 | Method Mismatch | Substitute works in general but not for the stated cooking method (e.g. a high-smoke-point fat recommended for baking instead of frying) | 0 | — (no instances found) |
| FM-05 | Alternative Count Violation | Bot provides 1 or 3+ alternatives instead of exactly 2 | 0 | — (all responses had exactly 2 alternatives) |
| FM-06 | Format Non-Compliance | Response missing required sections: ## Substituting, Role in dish, ### Best Substitute, ### Alternatives, ### Notes | 0 | — (all responses followed format correctly) |

**Model verdict: No failures found across 20 queries. claude-opus-4-5 followed all constraints correctly.**

---

## Part B — Checker Failure Modes

Failures the **automated checker** (error_analysis.py) made when evaluating responses.

| ID | Checker Bug | Description | Instances (V1) | Status |
|----|------------|-------------|---------------|--------|
| CB-01 | Original Ingredient False Flag | Checker flags a forbidden word that appears as a **reference to the original ingredient** (in ratio denominators, comparison phrases, or Notes) — not as a recommended substitute | 13 FPs in V1 → 8 FPs in V3 | ⚠️ Partially fixed |
| CB-02 | Unit Word Mismatch | Checker's ratio patterns only matched abbreviations (`tbsp`, `tsp`) — missed full words (`tablespoon`, `teaspoon`) | 2 FPs in V1 | ✅ Fixed in V2 |
| CB-03 | Safe Compound Gap | Compound phrase containing a forbidden word not in the safe masking list (e.g. `dairy-free cream cheeses` plural, `cheese substitutes`, `a Japanese soy sauce`) | 5 FPs in V1 | ⚠️ Partially fixed |

---

## CB-01 Detail — Original Ingredient False Flag Patterns

This is the dominant checker failure (8 remaining FPs). Five sub-patterns identified:

| Sub-pattern | Example text in response | IDs |
|-------------|--------------------------|-----|
| Ratio denominator | `per ¼ cup grated parmesan` / `per 1 cup almond flour` | 8, 12 |
| Comparison in Notes | `thinner than honey` / `similar mouthfeel to honey` | 5 |
| Warning text | `cross-contaminated with wheat` / `contains trace soy sauce` | 7 |
| Similarity comparison | `similarly to breadcrumbs` / `unlike gelatin` | 11, 18 |
| Plural not masked | `dairy-free cream cheeses` (singular safe compound doesn't match) | 20 |
| Partial context strip | `same amount as milk` (ratio strip incomplete) | 17 |

---

## Checker Iteration Summary

| Version | Total Flags | False Positives | True Negatives | TNR | Key Fix |
|---------|------------|----------------|---------------|-----|---------|
| V1 (baseline) | 15 | 13 | 7 | 35% | — |
| V2 | 11 | 11 | 9 | 45% | Full-word ratio units (tablespoon/teaspoon) |
| V3 (current) | 8 | 8 | 12 | **60%** | Ratio denominator stripping + expanded safe compounds |
| V4 (proposed) | ~2–3 | ~2–3 | ~17–18 | **~85%+** | Pass original ingredient dynamically; fix plurals |

---

## Proposed V4 Checker Fix

```python
# In check_dietary(), extract original from response heading and add to safe list
def check_dietary(response, restriction, original_ingredient=None):
    safe_compounds = list(DIETARY_SAFE_COMPOUNDS.get(restriction, []))
    if original_ingredient:
        # Add original + plural to safe masking
        safe_compounds.append(original_ingredient)
        safe_compounds.append(original_ingredient + "s")
    ...
```

Alternatively: use an LLM-based checker that understands context rather than keyword matching.

---

## Core Finding

> The model (claude-opus-4-5) made **zero failures** across all 20 substitution queries.
> All 8 remaining flags are **checker bugs** (CB-01 pattern).
> The eval bottleneck is checker quality, not model quality.
> Next step: fix the checker before adding more test queries.
