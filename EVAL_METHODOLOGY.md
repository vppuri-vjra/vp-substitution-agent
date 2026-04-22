# VP Substitution Agent — Overall Eval Methodology

**Course:** Understanding Evals  
**Project:** VP Substitution Agent (ingredient substitution chatbot)  
**Model:** claude-opus-4-5 | **Queries:** 20 | **Date:** April 2026

---

## The 3 Gulfs — Why We Built This

| Gulf | Question it answers | Our solution |
|------|-------------------|--------------|
| **Comprehension** | Can I understand what the model is doing at scale? | `error_analysis.py` checker + HTML viewer + `analysis_summary.md` |
| **Specification** | Does the model know exactly what I want? | 4-section system prompt + worked example (butter → coconut oil) |
| **Generalization** | Does it work across all real inputs, not just my test cases? | 20 queries across 4 dimensions (ingredient type, cooking method, dietary restriction, query clarity) |

---

## End-to-End Eval Steps

| Step | Part | Purpose | What | Grounded Theory Stage | Status | Location |
|------|------|---------|------|-----------------------|--------|----------|
| 1 | Part 1 | Define how the bot should behave | Write system prompt — 4 sections + worked example | — | ✅ Done | `prompts/system_prompt.txt` / GitHub |
| 2 | Part 2 | Create diverse inputs to stress-test the bot | Create 20 test queries across 4 dimensions | — | ✅ Done | `data/substitution_queries.csv` / GitHub |
| 3 | Part 2 | Record the methodology before running tests | Document 6 stages, 3 Gulfs, trace structure | — | ✅ Done | `SubEval_*.docx` / Downloads → Drive |
| 4 | Part 3 | Collect raw model responses at scale | Run bulk test — 20 queries → JSON results | — | ✅ Done | `results/results_20260419_150510.json` / GitHub |
| 5 | Part 3 | Browse responses without touching raw JSON | Generate HTML viewer with dimension badges + dietary filter | — | ✅ Done | `results/*.html` / local |
| 6 | Part 3 | Automatically flag potential failures | Run V4 rule-based checker on each response | 🔵 Open Coding | ✅ Done | `scripts/error_analysis.py` / GitHub |
| 7 | Part 3 | Separate real failures from checker mistakes | Human review → label TP / FP / TN / FN | 🔵 Open Coding | ✅ Done | `data/ground_truth.csv` / GitHub |
| 8 | Part 3 | Quantify how good the checker is | Compute TPR, TNR, Precision, FPR | 🔵 Open Coding | ✅ Done | `results/analysis_summary.md` / GitHub |
| 9 | Part 3 | Name and categorize what goes wrong | Build failure taxonomy — FM-01..FM-06, CB-01..CB-03 | 🟡 Axial Coding | ✅ Done | `failure_taxonomy.md` / GitHub |
| 10 | Part 3 | Apply grounded theory to the findings | Open → Axial → Selective coding — identify CB-01 as core failure | 🔴 Selective Coding | ✅ Done | `SubEval_GroundedTheory.docx` / Downloads |
| 11 | Part 3 | Prove the improvement with data | Fix checker V1→V4, re-run, compare before/after — TNR 35%→100% | — | ✅ Done | `scripts/error_analysis.py` / GitHub |
| 12 | Part 3 | Capture full methodology as reusable reference | Wrap-up doc — overall logical flow of eval | — | ✅ Done | `EVAL_METHODOLOGY.md` / GitHub |

---

## What the Checker Does (error_analysis.py)

| Check | How it works |
|-------|-------------|
| Format compliance | Regex — looks for `## Substituting`, `**Role in dish:**`, `### Best Substitute`, `### Alternatives`, `### Notes` |
| Ratio presence | Regex — matches `1:1`, `2 tablespoons`, `¾ cup`, `same amount`, etc. in Best Substitute section |
| Alternative count | Regex — counts numbered list items in Alternatives section, expects exactly 2 |
| Dietary compliance | Keyword matching with safe-compound masking + ratio denominator stripping + dynamic original ingredient masking |
| Repetition | Compares best substitute names across all responses |

---

## Checker Iteration History

| Version | Flags | TNR | Fix Applied |
|---------|-------|-----|------------|
| V1 (baseline) | 15 | 35% | — |
| V2 | 11 | 45% | Added full-word unit matching (`tablespoon`, `teaspoon`) |
| V3 | 8 | 60% | Ratio denominator stripping (`per N X`), extended safe compounds |
| V4 (final) | **0** | **100%** | Dynamic original ingredient masking from heading + `SAFE__` prefix placeholder |

---

## Failure Taxonomy Summary

### Model Failures (FM) — what the model could get wrong
| ID | Failure Mode | Found |
|----|-------------|-------|
| FM-01 | Dietary constraint violation | 0 |
| FM-02 | Missing or incorrect ratio | 0 |
| FM-03 | Wrong ingredient role | 0 |
| FM-04 | Method mismatch | 0 |
| FM-05 | Alternative count violation | 0 |
| FM-06 | Format non-compliance | 0 |

**Model verdict: Zero failures across 20 queries.**

### Checker Bugs (CB) — what the automated checker got wrong
| ID | Bug | V1 FPs | V4 Status |
|----|-----|--------|----------|
| CB-01 | Original ingredient false flag | 13 | ✅ Fixed |
| CB-02 | Unit word mismatch (tablespoon vs tbsp) | 2 | ✅ Fixed |
| CB-03 | Safe compound gaps (plurals, missing phrases) | 5 | ✅ Fixed |

---

## Final Metrics (V4 Checker)

| Metric | Value | Meaning |
|--------|-------|---------|
| TPR (Recall) | 0% | No real model failures existed to catch |
| TNR (Specificity) | **100%** | All 20 clean responses correctly cleared |
| FPR | **0%** | Zero false alarms |
| Precision | 0% | No flags raised (numerator = 0) |

---

## Key Insight

> The bottleneck was the **checker**, not the **model**.  
> claude-opus-4-5 followed every constraint correctly across all 20 queries.  
> The eval work was entirely about improving the automated checker's ability  
> to distinguish "original ingredient mentioned in context" from "forbidden ingredient recommended."

---

## Two-Layer Evaluation Pattern

A production eval system uses two layers — rule-based first, LLM-judge second.

```
Layer 1 — Rule-based (always runs)
    → Fast, free, catches obvious failures
    → Flags anything suspicious

Layer 2 — LLM-judge (runs after)
    → Reviews what rule-based flags
    → Catches what rules missed
    → Explains why something failed
```

### When to move from rule-based to LLM-judge

| Signal | What it means |
|---|---|
| Still seeing false positives after 2-3 iterations | Failure is meaning-based — rules can't fix it |
| V3+ and still chasing edge cases | Playing whack-a-mole — time to switch |
| Bug requires understanding context | Regex will never get there |
| Can't write a rule without breaking something else | Too many interdependencies |

### Rule-based vs LLM-judge — when to use each

| | Rule-based | LLM-judge |
|---|---|---|
| Cost | Free | API call per response |
| Speed | Instant | 3-5 seconds per response |
| At scale (10,000+ responses) | Cheap | Expensive |
| Consistency | Always same result | May vary slightly |
| Catches nuance | ❌ | ✅ |
| Explains failures | ❌ | ✅ |
| Best for | CI/CD pipelines, high volume | Edge cases, spot checks, where rules fail |

### Industry pattern
> Rule-based catches 90% of issues cheaply and fast.
> LLM-judge reviews flagged responses and edge cases the rules miss.
> Use both — not one or the other.

---

## LLM-as-Judge Results

**Judge prompt:** `prompts/judge_prompt.txt`  
**Script:** `scripts/llm_judge.py`  
**Criteria evaluated:** DIETARY, RATIO, ALTERNATIVES, FORMAT  

| Metric | Value |
|---|---|
| Judge Agreement Rate | **100% (20/20)** |
| Disagreements | 0 |
| Iterations needed | 1 (vs V1→V4 for rule-based) |

**Key finding:** LLM-judge achieved 100% agreement with human labels on the first attempt — no iteration needed — because Claude understands meaning rather than matching patterns.

---

## Files on GitHub

| File | What it is |
|------|-----------|
| `prompts/system_prompt.txt` | System prompt for the substitution bot |
| `prompts/judge_prompt.txt` | LLM-as-judge evaluation prompt |
| `data/substitution_queries.csv` | 20 test queries with dimension labels |
| `data/ground_truth.csv` | Human-reviewed labels (V4 — 20 TN) |
| `scripts/bulk_test.py` | Runs queries through Claude API |
| `scripts/error_analysis.py` | V4 automated checker |
| `scripts/llm_judge.py` | LLM-as-judge evaluator |
| `scripts/generate_viewer.py` | HTML viewer generator |
| `results/results_20260419_150510.json` | Raw bulk test output (20 responses) |
| `results/judge_results_20260422_090125.json` | LLM-judge scores for all 20 responses |
| `results/judge_vs_human.csv` | Judge scores vs human ground truth |
| `results/analysis_summary.md` | Metrics, confusion matrix, iteration history |
| `failure_taxonomy.md` | FM-01..FM-06 + CB-01..CB-03 taxonomy |
| `EVAL_METHODOLOGY.md` | This file — full methodology reference |
