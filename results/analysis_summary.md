# VP Substitution Agent — Error Analysis Summary

**Results file:** `results_20260419_150510.json`
**Model:** claude-opus-4-5 | **Total queries:** 20 | **Date:** 2026-04-19

---

## Per-Response Results

| ID | Status | Category | Dietary Restriction | Issue |
|----|--------|----------|--------------------|----|
| 01 | ✅ PASS | Fat | — | — |
| 02 | ✅ PASS | Binder | Vegan | — |
| 03 | ✅ PASS | Dairy | Dairy-free | — |
| 04 | ✅ PASS | Leavening base | Gluten-free | — |
| 05 | ⚠️ FLAG | Sweetener | Vegan | Vegan violation — found: honey |
| 06 | ✅ PASS | Leavening | — | — |
| 07 | ⚠️ FLAG | Flavor | Gluten-free | Gluten-free violation — found: wheat, soy sauce |
| 08 | ⚠️ FLAG | Leavening base | Nut-free | Nut-free violation — found: almond |
| 09 | ✅ PASS | Dairy | Dairy-free | — |
| 10 | ✅ PASS | Thickener | — | — |
| 11 | ⚠️ FLAG | Binder | Vegan | Vegan violation — found: cream, gelatin |
| 12 | ⚠️ FLAG | Flavor | Dairy-free | Dairy-free violation — found: parmesan |
| 13 | ✅ PASS | Liquid/flavor | — | — |
| 14 | ✅ PASS | Binder | — | — |
| 15 | ✅ PASS | Sweetener | — | — |
| 16 | ✅ PASS | Fat | — | — |
| 17 | ⚠️ FLAG | Dairy | Dairy-free | Dairy-free violation — found: milk |
| 18 | ⚠️ FLAG | Binder | Gluten-free | Gluten-free violation — found: breadcrumbs |
| 19 | ✅ PASS | Fat/binder | Vegan | — |
| 20 | ⚠️ FLAG | Dairy | Dairy-free | Dairy-free violation — found: cream, cheese |

---

## Failure Taxonomy (Checker Flags)

| Count | Failure Type | Affected IDs |
|-------|-------------|--------------|
| 3x | Dairy-free violation in substitute | 12, 17, 20 |
| 2x | Gluten-free violation in substitute | 7, 18 |
| 2x | Vegan violation in substitute | 5, 11 |
| 1x | Nut-free violation in substitute | 8 |

**Repetition check:** ✅ No duplicate substitutes across 20 responses

---

## Summary

| Metric | Value |
|--------|-------|
| Total queries | 20 |
| Checker flags | 8 |
| Affected IDs | 5, 7, 8, 11, 12, 17, 20 |
| Clean responses | 12 |

---

## Confusion Matrix (V3 Checker vs Human Ground Truth)

|  | Checker: FAIL | Checker: PASS |
|--|--------------|--------------|
| **Reality: FAIL** | TP = 0 | FN = 0 |
| **Reality: PASS** | FP = 8 | TN = 12 |

---

## Checker Performance Metrics

| Metric | Formula | Value | Meaning |
|--------|---------|-------|---------|
| TPR (Recall) | TP / (TP + FN) | 0% | No real failures in dataset to catch |
| TNR (Specificity) | TN / (TN + FP) | **60%** | Of 20 clean responses, 12 correctly cleared |
| FPR | FP / (FP + TN) | 40% | 8 false alarms raised |
| Precision | TP / (TP + FP) | 0% | All 8 flags were false alarms |

---

## Human Review Findings (Step 7)

All 8 remaining checker flags are **False Positives**. Root cause: the forbidden-word checker sees the **original ingredient mentioned in comparison/ratio text**, not as a recommended substitute.

| Pattern | Example | IDs |
|---------|---------|-----|
| Comparison in Notes | "thinner than honey", "similar mouthfeel to honey" | 5 |
| Original in ratio denominator | "per ¼ cup grated parmesan" | 12 |
| Warning about original | "cross-contaminated with wheat", "contains trace soy sauce" | 7 |
| Comparison baseline | "similarly to breadcrumbs" | 18 |
| Plural not masked | "dairy-free cream cheeses" (singular safe compound) | 20 |
| Original in panna cotta | "cream mixture", "unlike gelatin" | 11 |
| Original in ratio | "same amount as milk" (partial strip) | 17 |
| Original in alternative | "per 1 cup almond flour" (ratio denominator) | 8 |

---

## Checker Iteration History

| Version | Flags | IDs Affected | TNR | Root Cause Fixed |
|---------|-------|-------------|-----|-----------------|
| V1 (baseline) | 15 | 13 | 35% | — |
| V2 | 11 | 11 | 45% | Full-word ratio units (tablespoon/teaspoon) |
| V3 (current) | 8 | 8 | **60%** | Ratio denominator stripping + expanded safe compounds |
| V4 (proposed) | ~2–3 | ~2–3 | ~85%+ | Pass original ingredient to checker; plurals in safe compounds |

---

## Proposed V4 Fix

The remaining 8 FPs share one root cause: the checker doesn't know what the **original ingredient** is. Fix:

1. Pass `original_ingredient` extracted from the query into `check_dietary()`
2. Dynamically add it to the safe compound masking list
3. Add plural forms (`cheeses`, `creams`) to safe compound matching
4. Add `"similarly to X"`, `"unlike X"` to comparison phrase stripping
