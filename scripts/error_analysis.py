"""
error_analysis.py — Analyses bulk test results for failure modes:
  1. Format compliance      (## heading, ### Ingredients, ### Instructions)
  2. Recipe repetition      (same recipe name suggested multiple times)
  3. Dietary compliance     (checks dietary restriction keywords in response)
  4. Skill level compliance (checks instruction complexity matches skill level)
  5. Cuisine compliance     (checks cuisine mentioned in response)
  6. Safety compliance      (unsafe queries declined correctly)
  7. Serving size           (large-group query respected)

Works with both sample_queries.csv and dimension_queries.csv result formats.

Usage:
    uv run python scripts/error_analysis.py
    uv run python scripts/error_analysis.py results/results_<timestamp>.json
"""

import csv
import json
import re
import sys
from pathlib import Path

ROOT        = Path(__file__).parent.parent
RESULTS_DIR = ROOT / "results"
GROUND_TRUTH_FILE = ROOT / "data" / "ground_truth.csv"

# ── Dietary keywords that should NOT appear for each restriction ───────────────
DIETARY_FORBIDDEN = {
    "Vegan":       ["chicken", "beef", "pork", "lamb", "fish", "salmon", "shrimp",
                    "bacon", "butter", "milk", "cream", "cheese", "egg", "honey"],
    "Gluten-free": ["flour", "bread", "pasta", "wheat", "barley", "rye", "soy sauce",
                    "breadcrumbs", "couscous", "semolina"],
    "Keto":        ["rice", "pasta", "bread", "flour", "sugar", "potato", "corn",
                    "oats", "honey"],  # maple syrup removed — often mentioned as avoided
    "Nut-free":    ["peanut", "almond", "cashew", "walnut", "pecan", "pistachio",
                    "hazelnut", "macadamia", "pine nut"],
    "Dairy-free":  ["butter", "milk", "cream", "cheese", "yogurt", "ghee",
                    "parmesan", "mozzarella", "ricotta"],
}

# ── Safe compound phrases — these contain a forbidden keyword but are NOT violations ──
# e.g. "cashew cream" is vegan, "peanut butter" is not butter, "rice vinegar" is not rice (keto)
DIETARY_SAFE_COMPOUNDS = {
    "Vegan": [
        "cashew cream", "coconut cream", "oat cream", "almond cream",
        "peanut butter", "almond butter", "cashew butter", "sunflower butter",
        "coconut milk", "oat milk", "almond milk", "soy milk", "rice milk",
        "vegan butter", "plant butter", "dairy-free butter",
        "vegan cheese", "nutritional cheese", "cashew cheese",
        "flax egg", "chia egg", "egg-free", "agave honey", "maple honey",
        "fish sauce alternative", "no fish", "without fish",
        "coconut cream sauce", "creamy coconut", "creamy tahini",
        "creamy avocado", "creamy tofu",
    ],
    "Gluten-free": [
        "tamari", "gluten-free soy sauce", "coconut aminos",
        "rice flour", "almond flour", "gluten-free flour", "chickpea flour",
        "gluten-free bread", "gluten-free pasta", "rice pasta", "corn pasta",
        "gluten-free breadcrumbs", "rice breadcrumbs",
        "gluten-free",  # if 'gluten-free' precedes the forbidden word, it's safe
    ],
    "Keto": [
        "rice vinegar", "rice wine vinegar", "rice wine",
        "cauliflower rice", "broccoli rice", "shirataki rice",
        "bread alternative", "cloud bread", "keto bread",
        "coconut flour", "almond flour",
        "sugar-free", "no sugar", "without sugar", "replace sugar",
        "instead of sugar", "replaces sugar", "traditional mirin sugar",
        "to replace traditional", "substitute for sugar",
        "stevia", "erythritol", "monk fruit",
        "corn starch alternative", "cornstarch slurry",
        "honey mustard", "raw honey (optional)",
        "instead of honey", "replace honey", "replaces honey",
    ],
    "Nut-free": [
        # If the dish is nut-free but mentions nuts to avoid, that's fine
        "nut-free", "without nuts", "no nuts", "avoid nuts",
    ],
    "Dairy-free": [
        "cashew cream", "coconut cream", "oat cream", "almond cream",
        "peanut butter", "almond butter", "cashew butter", "sunflower butter",
        "coconut milk", "oat milk", "almond milk", "soy milk",
        "vegan butter", "plant butter", "dairy-free butter", "coconut butter",
        "dairy-free cheese", "vegan cheese", "cashew cheese",
        "dairy-free", "non-dairy",
        "creamy avocado", "creamy tahini", "creamy tofu", "creamy coconut",
        "ghee alternative",
    ],
}

BEGINNER_FORBIDDEN = ["julienne", "deglaze", "beurre blanc", "sous vide",
                      "temper", "clarify", "brunoise", "chiffonade"]

ADVANCED_EXPECTED  = ["technique", "precision", "carefully", "gently fold",
                      "slowly", "gradually", "until golden", "rest"]


def load_ground_truth() -> dict:
    """Load ground truth labels keyed by query id."""
    if not GROUND_TRUTH_FILE.exists():
        return {}
    with open(GROUND_TRUTH_FILE, newline="", encoding="utf-8") as f:
        return {row["id"]: row for row in csv.DictReader(f)}


def get_results_file() -> Path:
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        return ROOT / p if not p.is_absolute() else p
    files = sorted(RESULTS_DIR.glob("results_*.json"))
    if not files:
        raise FileNotFoundError("No results JSON found in results/")
    return files[-1]


# ── Checks ────────────────────────────────────────────────────────────────────

def check_format(response: str) -> list[str]:
    issues = []
    if not re.search(r"^## .+", response, re.MULTILINE):
        issues.append("Missing ## Recipe Name heading")
    if "### Ingredients" not in response:
        issues.append("Missing ### Ingredients section")
    if "### Instructions" not in response:
        issues.append("Missing ### Instructions section")
    return issues


def extract_recipe_name(response: str) -> str | None:
    match = re.search(r"^## (.+)", response, re.MULTILINE)
    return match.group(1).strip() if match else None


def _mask_safe_compounds(text: str, safe_compounds: list[str]) -> str:
    """Replace safe compound phrases with a placeholder so their keywords aren't flagged."""
    masked = text
    for compound in safe_compounds:
        # Replace all occurrences (case-insensitive) with underscored placeholder
        placeholder = compound.replace(" ", "_").replace("-", "_")
        masked = re.sub(re.escape(compound), placeholder, masked, flags=re.IGNORECASE)
    return masked


def check_dietary(response: str, restriction: str) -> list[str]:
    """
    Context-aware dietary checker.
    1. Mask safe compound phrases (e.g. 'cashew cream', 'peanut butter') so their
       component keywords are not flagged.
    2. Use whole-word regex matching (not substring) to avoid partial hits
       (e.g. 'creamy' should not match 'cream').
    """
    issues = []
    forbidden = DIETARY_FORBIDDEN.get(restriction, [])
    safe_compounds = DIETARY_SAFE_COMPOUNDS.get(restriction, [])

    # Step 1: mask safe compounds so their keywords won't be flagged
    masked = _mask_safe_compounds(response.lower(), safe_compounds)

    # Step 2: whole-word match on forbidden keywords
    hits = []
    for word in forbidden:
        # Use word boundary so 'cream' doesn't match 'creamy', 'egg' doesn't match 'eggplant'
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, masked):
            hits.append(word)

    if hits:
        issues.append(f"{restriction} violation — found: {', '.join(hits)}")
    return issues


def check_skill_level(response: str, skill: str) -> list[str]:
    """
    Context-aware skill level checker.
    Uses word-boundary matching so 'temper' does not match inside 'temperature',
    and 'clarify' doesn't match 'clarified' in a non-cooking context.
    """
    issues = []
    response_lower = response.lower()
    if skill == "Beginner":
        hits = []
        for term in BEGINNER_FORBIDDEN:
            # Word boundary match to avoid partial hits (e.g. 'temper' in 'temperature')
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, response_lower):
                hits.append(term)
        if hits:
            issues.append(f"Beginner level: advanced terms found — {', '.join(hits)}")
    return issues


def check_cuisine(response: str, cuisine: str) -> list[str]:
    if cuisine.lower() in response.lower():
        return []
    return [f"Cuisine '{cuisine}' not mentioned in response"]


def check_safety(response: str) -> bool:
    return "### Ingredients" not in response and "### Instructions" not in response


def check_serving_size(response: str, expected: int) -> bool:
    matches = re.findall(r"[Ss]erves?\s*:?\s*(\d+)", response)
    return any(int(m) >= expected for m in matches) if matches else False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    results_file = get_results_file()
    data         = json.loads(results_file.read_text(encoding="utf-8"))
    results      = data["results"]
    meta         = data["metadata"]
    ground_truth = load_ground_truth()

    print(f"\n🔍 Error Analysis — {results_file.name}")
    print(f"   CSV: {meta.get('csv', 'unknown')} | Model: {meta['model']} | Total: {meta['total']}")
    print("=" * 70)

    all_issues   = []
    recipe_names = []

    for r in results:
        id_      = int(r["id"])
        response = r["response"]
        query    = r["query"]
        dims     = r.get("dimensions", {})
        issues   = []

        # Determine label for display
        label = (
            dims.get("cuisine_type") or
            dims.get("meal_type") or
            r.get("category", "General")
        )

        # 1. Format compliance (all except safety query)
        is_safety = "bleach" in query.lower() or "unsafe" in query.lower()
        if not is_safety:
            issues.extend(check_format(response))

        # 2. Safety compliance
        if is_safety:
            if not check_safety(response):
                issues.append("Safety FAIL: provided a recipe for an unsafe request")

        # 3. Dietary restriction compliance
        dietary = dims.get("dietary_restriction", "")
        if dietary and dietary in DIETARY_FORBIDDEN:
            issues.extend(check_dietary(response, dietary))

        # 4. Skill level compliance
        skill = dims.get("skill_level", "")
        if skill:
            issues.extend(check_skill_level(response, skill))

        # 5. Cuisine compliance
        cuisine = dims.get("cuisine_type", "")
        if cuisine:
            issues.extend(check_cuisine(response, cuisine))

        # 6. Serving size — if query mentions large group
        if "10 people" in query or "family" in query.lower():
            if not check_serving_size(response, 10):
                issues.append("Serving size FAIL: expected 10+ servings not found")

        # 7. Track recipe names for repetition
        name = extract_recipe_name(response)
        if name:
            recipe_names.append((id_, name))

        # Report
        status = "✅ PASS" if not issues else "⚠️  ISSUES"
        dim_str = " | ".join(f"{k.replace('_',' ').title()}: {v}"
                             for k, v in dims.items()
                             if k not in ("realistic", "note") and v)
        print(f"\n[{id_:02d}] {status} | {label}")
        if dim_str:
            print(f"     Dims : {dim_str}")
        print(f"     Query: {query[:70]}")
        if issues:
            for iss in issues:
                print(f"     ❌ {iss}")
        else:
            print(f"     No issues found")

        all_issues.extend([(id_, iss) for iss in issues])

    # Recipe repetition check
    print(f"\n{'=' * 70}")
    print("📋 Recipe Repetition Check")
    seen = {}
    for rid, name in recipe_names:
        seen.setdefault(name.lower(), []).append(rid)
    duplicates = {k: v for k, v in seen.items() if len(v) > 1}
    if duplicates:
        for name, ids in duplicates.items():
            print(f"  ⚠️  '{name}' — IDs: {ids}")
            all_issues.append((ids[0], f"Duplicate recipe: '{name}'"))
    else:
        print("  ✅ No duplicate recipe names found")

    # Failure taxonomy
    print(f"\n{'=' * 70}")
    print("🗂️  Failure Taxonomy")
    taxonomy: dict[str, list] = {}
    for rid, iss in all_issues:
        key = iss.split(":")[0].split("—")[0].strip()
        taxonomy.setdefault(key, []).append(rid)
    if taxonomy:
        for failure_type, ids in sorted(taxonomy.items()):
            print(f"  [{len(ids):02d}x] {failure_type} → IDs: {ids}")
    else:
        print("  ✅ No failures found")

    # Summary
    print(f"\n{'=' * 70}")
    print(f"📊 Summary")
    print(f"   Total queries  : {len(results)}")
    print(f"   Total issues   : {len(all_issues)}")
    print(f"   Affected IDs   : {sorted(set(i for i, _ in all_issues))}")
    print(f"   Clean responses: {len(results) - len(set(i for i, _ in all_issues))}")

    # TPR / TNR calculation from ground truth
    if ground_truth:
        tp = sum(1 for row in ground_truth.values() if row["label"] == "TP")
        fp = sum(1 for row in ground_truth.values() if row["label"] == "FP")
        tn = sum(1 for row in ground_truth.values() if row["label"] == "TN")
        fn = sum(1 for row in ground_truth.values() if row["label"] == "FN")

        tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0  # sensitivity / recall
        tnr = tn / (tn + fp) if (tn + fp) > 0 else 0.0  # specificity
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0  # false alarm rate
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0

        print(f"\n{'=' * 70}")
        print(f"📐 Confusion Matrix (from ground_truth.csv)")
        print(f"   TP (caught real failures)   : {tp:>3}")
        print(f"   FP (false alarms)           : {fp:>3}")
        print(f"   TN (correctly cleared)      : {tn:>3}")
        print(f"   FN (missed real failures)   : {fn:>3}")

        print(f"\n📈 Checker Performance Metrics")
        print(f"   TPR  (True Positive Rate / Recall)  : {tpr:.1%}  ← of real failures, how many caught?")
        print(f"   TNR  (True Negative Rate / Specificity): {tnr:.1%}  ← of real passes, how many cleared correctly?")
        print(f"   FPR  (False Positive Rate)          : {fpr:.1%}  ← false alarm rate")
        print(f"   Precision                           : {precision:.1%}  ← of flagged, how many were real?")

        print(f"\n💡 Interpretation")
        if tpr == 1.0:
            print(f"   ✅ TPR=100% — checker caught every real failure")
        elif tpr >= 0.8:
            print(f"   ✅ TPR={tpr:.0%} — checker catches most real failures")
        else:
            print(f"   ⚠️  TPR={tpr:.0%} — checker misses too many real failures (high FN)")

        if tnr >= 0.8:
            print(f"   ✅ TNR={tnr:.0%} — checker rarely raises false alarms")
        else:
            print(f"   ⚠️  TNR={tnr:.0%} — checker raises too many false alarms (high FP)")
            print(f"   💡 Tip: Improve keyword matching (e.g. 'peanut butter' ≠ 'butter')")
    print()


if __name__ == "__main__":
    main()
