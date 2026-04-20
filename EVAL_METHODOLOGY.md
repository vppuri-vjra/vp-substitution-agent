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
| 11 | Stage 6 | Prove the improvement with data | Fix checker V1→V4, re-run, compare before/after — TNR 35%→100% | — | ✅ Done | `scripts/error_analysis.py` / GitHub |
| 12 | Stage 6 | Capture full methodology as reusable reference | Wrap-up doc — overall logical flow of eval | — | ✅ Done | `EVAL_METHODOLOGY.md` / GitHub |

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
