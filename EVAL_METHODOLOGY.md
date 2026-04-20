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

| Step | Task | Deliverable | Purpose |
|------|------|------------|---------|
| 1 | Write system prompt | `prompts/system_prompt.txt` | Bridge Gulf of Specification — tell model Role, Rules, Agency, Format + worked example |
| 2 | Design test queries | `data/substitution_queries.csv` | Bridge Gulf of Generalization — 20 queries across 4 dimensions, including edge cases |
| 3 | Write course docs | `SubEval_Trace.docx`, `SubEval_BigPicture.docx`, `SubEval_GroundedTheory.docx` | Document methodology (Trace definition, 3 Gulfs, Grounded Theory coding plan) |
| 4 | Run bulk test | `results/results_20260419_150510.json` | Send all 20 queries through Claude API, collect responses |
| 5 | Build HTML viewer | `results/*.html` | Bridge Gulf of Comprehension — browse all responses with dimension badges and dietary filter |
| 6 | Automated checking | `scripts/error_analysis.py` | Flag potential failures: format, ratio, dietary compliance, alternative count, repetition |
| 7 | Human review | `data/ground_truth.csv` | Label each flag as TP / FP / TN / FN — establish ground truth |
| 8 | Compute metrics | `results/analysis_summary.md` | Confusion matrix → TPR, TNR, FPR, Precision |
| 9 | Build failure taxonomy | `failure_taxonomy.md` | Name and categorize failure patterns (model FM-01..FM-06, checker CB-01..CB-03) |
| 10 | Grounded theory coding | `SubEval_GroundedTheory.docx` (filled) | Open → Axial → Selective coding on actual findings |
| 11 | Iterate checker | `scripts/error_analysis.py` V1→V4 | Fix root cause, re-run, compare before/after metrics |
| 12 | Wrap-up doc | `EVAL_METHODOLOGY.md` (this file) | Capture full methodology as a reusable reference |

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

## Files on GitHub

| File | What it is |
|------|-----------|
| `prompts/system_prompt.txt` | System prompt for the substitution bot |
| `data/substitution_queries.csv` | 20 test queries with dimension labels |
| `data/ground_truth.csv` | Human-reviewed labels (V4 — 20 TN) |
| `scripts/bulk_test.py` | Runs queries through Claude API |
| `scripts/error_analysis.py` | V4 automated checker |
| `scripts/generate_viewer.py` | HTML viewer generator |
| `results/results_20260419_150510.json` | Raw bulk test output (20 responses) |
| `results/analysis_summary.md` | Metrics, confusion matrix, iteration history |
| `failure_taxonomy.md` | FM-01..FM-06 + CB-01..CB-03 taxonomy |
| `EVAL_METHODOLOGY.md` | This file — full methodology reference |
