"""
error_analysis.py — Analyses bulk test results for the VP Substitution Agent.

Checks per response:
  1. Format compliance      (## Substituting heading, Role in dish, ### Best Substitute,
                             ### Alternatives, ### Notes)
  2. Ratio presence         (every substitute must include a ratio)
  3. Alternative count      (exactly 2 alternatives required)
  4. Dietary compliance     (substitute must not violate stated restriction)
  5. Repetition             (same substitution suggested for multiple queries)

Usage:
    uv run python scripts/error_analysis.py
    uv run python scripts/error_analysis.py results/results_<timestamp>.json
"""

import csv
import json
import re
import sys
from pathlib import Path

ROOT              = Path(__file__).parent.parent
RESULTS_DIR       = ROOT / "results"
GROUND_TRUTH_FILE = ROOT / "data" / "ground_truth.csv"

# ── Dietary forbidden keywords ─────────────────────────────────────────────────
# These should NOT appear in the RECOMMENDED substitute (not the original ingredient)
DIETARY_FORBIDDEN = {
    "Vegan":       ["chicken", "beef", "pork", "lamb", "fish", "salmon", "shrimp",
                    "bacon", "butter", "milk", "cream", "cheese", "egg", "honey",
                    "gelatin", "lard"],
    "Gluten-free": ["flour", "wheat", "barley", "rye", "soy sauce", "breadcrumbs",
                    "semolina", "couscous"],
    "Dairy-free":  ["butter", "milk", "cream", "cheese", "yogurt", "ghee",
                    "parmesan", "mozzarella", "ricotta", "buttermilk", "whey",
                    "cheddar", "brie", "gouda"],
    "Nut-free":    ["almond", "cashew", "walnut", "pecan", "pistachio",
                    "hazelnut", "macadamia", "pine nut", "peanut"],
}

# ── Safe compound phrases — contain a forbidden word but are NOT violations ────
DIETARY_SAFE_COMPOUNDS = {
    "Vegan": [
        "cashew cream", "coconut cream", "oat cream", "almond cream",
        "peanut butter", "almond butter", "cashew butter", "sunflower butter",
        "coconut milk", "oat milk", "almond milk", "soy milk", "rice milk",
        "vegan butter", "plant butter", "dairy-free butter",
        "vegan cheese", "cashew cheese", "nutritional yeast",
        "flax egg", "chia egg", "egg-free", "no egg",
        "agave", "maple syrup",
        "agar agar", "agar-agar",
        "creamy coconut", "creamy avocado", "creamy tofu",
        "fish sauce alternative", "vegan fish",
        "cream mixture", "cream base", "the cream",
        "vegan cream", "cream-based", "plant-based cream",
    ],
    "Gluten-free": [
        "tamari", "gluten-free soy sauce", "coconut aminos",
        "rice flour", "almond flour", "gluten-free flour", "chickpea flour",
        "oat flour", "tapioca flour", "arrowroot flour",
        "gluten-free breadcrumbs", "almond meal",
        "gluten-free", "wheat-free",
        "all-purpose flour", "wheat-based", "wheat flour",
        "regular breadcrumbs", "wheat breadcrumbs",
        "a japanese soy sauce", "japanese soy sauce",
    ],
    "Dairy-free": [
        "cashew cream", "coconut cream", "oat cream", "almond cream",
        "peanut butter", "almond butter", "cashew butter",
        "coconut milk", "oat milk", "almond milk", "soy milk", "rice milk",
        "vegan butter", "plant butter", "dairy-free butter", "coconut butter",
        "dairy-free cream cheese", "dairy-free cheese", "vegan cheese",
        "cashew cheese", "cashew cream cheese", "nutritional yeast",
        "dairy-free", "non-dairy", "lactose-free",
        "creamy avocado", "creamy tahini", "creamy tofu", "creamy coconut",
        "coconut yogurt", "soy yogurt",
        "dairy-free buttermilk", "vegan buttermilk",
        "vegan parmesan", "dairy-free parmesan", "cheese substitute",
        "cheese substitutes", "cheese alternative",
        "heavy cream's", "heavy cream alternative", "heavy cream",
        "traditional buttermilk", "regular buttermilk",
    ],
    "Nut-free": [
        "nut-free", "without nuts", "no nuts", "avoid nuts",
        "sunflower butter", "seed butter", "tahini",
        "oat flour", "seed-based",
    ],
}

# ── Ratio patterns — at least one must appear in the Best Substitute section ──
RATIO_PATTERNS = [
    r'\d+\s*:\s*\d+',                                              # 1:1, 2:1
    r'\d+/\d+\s+cup',                                              # ½ cup, ¾ cup
    r'(½|¼|¾|⅓|⅔)\s*(cup|tsp|tbsp|tablespoon|teaspoon)',          # unicode fractions
    r'\d+(\.\d+)?\s*(cup|tbsp|tsp|tablespoon|teaspoon|g|ml|oz)s?', # 0.75 cup, 2 tbsp, 2 tablespoons
    r'same amount',                                                 # "use the same amount"
    r'equal amount',
    r'1:1',
    r'per\s+\d+\s+(cup|tbsp|tsp|tablespoon|teaspoon)',             # per 1 cup / per 1 tablespoon
    r'\d+\s*(cup|tbsp|tsp|tablespoon|teaspoon)s?\s+per',          # 2 tbsp per / 2 tablespoons per
    r'replace.{1,30}with.{1,30}\d',                               # replace X with 2 tbsp
    r'use\s+(half|double|twice)',                                  # use half the amount
]


def load_ground_truth() -> dict:
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
    """Check substitution bot format compliance."""
    issues = []
    if not re.search(r"^## Substituting .+", response, re.MULTILINE | re.IGNORECASE):
        issues.append("Missing '## Substituting X in Y' heading")
    if not re.search(r"\*\*Role in dish", response, re.IGNORECASE):
        issues.append("Missing '**Role in dish:**' line")
    if "### Best Substitute" not in response:
        issues.append("Missing ### Best Substitute section")
    if "### Alternatives" not in response:
        issues.append("Missing ### Alternatives section")
    if "### " in response and "Notes" not in response:
        issues.append("Missing ### Notes section")
    return issues


def check_ratio(response: str) -> list[str]:
    """Check that at least one ratio is present in the Best Substitute section."""
    # Extract just the Best Substitute section
    match = re.search(r"### Best Substitute(.+?)###", response, re.DOTALL)
    section = match.group(1) if match else response

    for pattern in RATIO_PATTERNS:
        if re.search(pattern, section, re.IGNORECASE):
            return []
    return ["Missing substitution ratio in Best Substitute section"]


def check_alternative_count(response: str) -> list[str]:
    """Check that exactly 2 alternatives are listed."""
    match = re.search(r"### Alternatives(.+?)###", response, re.DOTALL)
    if not match:
        return ["Missing ### Alternatives section"]
    section = match.group(1)
    # Count numbered list items: 1. or 2.
    items = re.findall(r"^\s*\d+\.", section, re.MULTILINE)
    count = len(items)
    if count == 2:
        return []
    return [f"Alternative count: expected 2, found {count}"]


def _mask_safe_compounds(text: str, safe_compounds: list[str]) -> str:
    """
    Longest compounds first so 'dairy-free cream cheese' masks before 'cream'.
    Placeholder uses SAFE__ prefix so single-word compounds (e.g. 'honey' → 'SAFE__honey')
    can never be re-matched by the forbidden-word checker.
    """
    masked = text
    for compound in sorted(safe_compounds, key=len, reverse=True):
        placeholder = "SAFE__" + re.sub(r'[\s\-]', '_', compound)
        masked = re.sub(re.escape(compound), placeholder, masked, flags=re.IGNORECASE)
    return masked


def _mask_ratio_denominators(text: str) -> str:
    """
    Remove ratio denominators and comparison phrases that reference the original ingredient.
    e.g. 'per 1 egg', 'per 1 cup buttermilk', 'same amount as milk', 'thinner than honey'
    These are measurement references to what's being replaced, not recommendations.
    """
    # "per [fraction/number] [anything up to end of phrase]"
    # Handles: "per 1 cup buttermilk", "per ¼ cup grated parmesan", "per 1 egg", "per 1 tablespoon"
    text = re.sub(r'\bper\s+(?:\d+|½|¼|¾|⅓|⅔)[\s\w\-\']{0,40}', '', text, flags=re.IGNORECASE)
    # "same amount as X", "similar to X", "compared to X", "similar mouthfeel to X"
    text = re.sub(r'\b(same amount as|same as|similar to|compared to|mouthfeel to|equivalent to)\s+[\w\s\-\']{1,50}', '', text, flags=re.IGNORECASE)
    # "[adjective] than X" — "thinner than honey", "less than X", "closer than X"
    text = re.sub(r'\b\w+\s+than\s+[\w\s\-]{1,40}', '', text, flags=re.IGNORECASE)
    # "mimics X", "mirrors X", "replaces X", "substitute for X"
    text = re.sub(r'\b(mimics|mirrors|replaces|substitute for|replacing)\s+[\w\s\-\']{1,50}', '', text, flags=re.IGNORECASE)
    # "cross-contaminated with X"
    text = re.sub(r'\bcross.contaminated\s+with\s+[\w\s]{1,30}', '', text, flags=re.IGNORECASE)
    # "trace X" (e.g. trace wheat)
    text = re.sub(r'\btrace\s+\w+', '', text, flags=re.IGNORECASE)
    # "still contain[s] [trace] X"
    text = re.sub(r'\bstill\s+contain[s]?\s+(?:trace\s+)?\w+', '', text, flags=re.IGNORECASE)
    # "a [adjective] X" when describing what the original is (e.g. "a Japanese soy sauce")
    text = re.sub(r'\ba\s+\w+\s+soy sauce\b', '', text, flags=re.IGNORECASE)
    # "little to no X", "with little to no X" — describing original ingredient composition
    text = re.sub(r'\blittle\s+to\s+no\s+\w+', '', text, flags=re.IGNORECASE)
    # "traditionally X-based", "cream-based", "wheat-based" — describing original dish nature
    text = re.sub(r'\btraditionally\s+\w+', '', text, flags=re.IGNORECASE)
    return text


def extract_original_ingredient(response: str) -> list[str]:
    """
    Extract the original ingredient being substituted from the ## heading.
    e.g. '## Substituting Heavy Cream in Pasta Sauce' → ['heavy cream', 'heavy creams']
    Returns a list of forms (singular + plural) to add to safe masking.
    """
    match = re.search(r"^## Substituting (.+?) (?:in|for|from)\b", response, re.MULTILINE | re.IGNORECASE)
    if not match:
        return []
    raw = match.group(1).strip().lower()
    forms = [raw]
    # Add plural: simple 's' suffix if not already plural
    if not raw.endswith("s"):
        forms.append(raw + "s")
    # Add common variant — split multi-word and add each word that's >4 chars
    words = [w for w in raw.split() if len(w) > 4]
    forms.extend(words)
    forms.extend(w + "s" for w in words if not w.endswith("s"))
    return list(set(forms))


def check_dietary(response: str, restriction: str) -> list[str]:
    """
    V4 context-aware dietary checker for the substitution bot.
    - Only checks the Best Substitute + Alternatives sections
    - Strips ratio denominators and comparison phrases
    - Dynamically adds the original ingredient (from heading) to safe masking
      so references like 'per 1 cup buttermilk' or 'similar to honey' don't trigger
    """
    forbidden      = DIETARY_FORBIDDEN.get(restriction, [])
    safe_compounds = list(DIETARY_SAFE_COMPOUNDS.get(restriction, []))

    # V4: dynamically add original ingredient + variants to safe list
    original_forms = extract_original_ingredient(response)
    safe_compounds.extend(original_forms)

    # Only check the recommended substitute sections, not the heading
    match = re.search(r"### Best Substitute(.+)", response, re.DOTALL | re.IGNORECASE)
    check_section = match.group(1) if match else response

    # Strip ratio denominators and comparison text before checking
    check_section = _mask_ratio_denominators(check_section)

    masked = _mask_safe_compounds(check_section.lower(), safe_compounds)

    hits = []
    for word in forbidden:
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, masked):
            hits.append(word)

    if hits:
        return [f"{restriction} violation in substitute — found: {', '.join(hits)}"]
    return []


def extract_best_substitute(response: str) -> str | None:
    """Extract the Best Substitute name for repetition checking."""
    match = re.search(r"### Best Substitute\s*\n\*\*(.+?)\*\*", response)
    return match.group(1).strip() if match else None


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    results_file = get_results_file()
    data         = json.loads(results_file.read_text(encoding="utf-8"))
    results      = data["results"]
    meta         = data["metadata"]
    ground_truth = load_ground_truth()

    print(f"\n🔍 Substitution Error Analysis — {results_file.name}")
    print(f"   CSV: {meta.get('csv', 'unknown')} | Model: {meta['model']} | Total: {meta['total']}")
    print("=" * 70)

    all_issues      = []
    substitute_names = []

    for r in results:
        id_      = int(r["id"])
        response = r["response"]
        query    = r["query"]
        dims     = r.get("dimensions", {})
        issues   = []

        label = (
            dims.get("ingredient_type") or
            dims.get("dietary_restriction") or
            "General"
        )

        # 1. Format compliance
        issues.extend(check_format(response))

        # 2. Ratio presence
        issues.extend(check_ratio(response))

        # 3. Alternative count
        issues.extend(check_alternative_count(response))

        # 4. Dietary restriction compliance
        dietary = dims.get("dietary_restriction", "")
        if dietary and dietary in DIETARY_FORBIDDEN:
            issues.extend(check_dietary(response, dietary))

        # 5. Track best substitute for repetition check
        name = extract_best_substitute(response)
        if name:
            substitute_names.append((id_, name))

        # Report
        status  = "✅ PASS" if not issues else "⚠️  ISSUES"
        dim_str = " | ".join(
            f"{k.replace('_', ' ').title()}: {v}"
            for k, v in dims.items()
            if k not in ("realistic", "note") and v and v != "None"
        )
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

    # Repetition check
    print(f"\n{'=' * 70}")
    print("📋 Substitute Repetition Check")
    seen = {}
    for rid, name in substitute_names:
        seen.setdefault(name.lower(), []).append(rid)
    duplicates = {k: v for k, v in seen.items() if len(v) > 1}
    if duplicates:
        for name, ids in duplicates.items():
            print(f"  ⚠️  '{name}' suggested for IDs: {ids}")
            all_issues.append((ids[0], f"Duplicate substitute: '{name}'"))
    else:
        print("  ✅ No duplicate substitutes found")

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

    # TPR / TNR from ground truth
    if ground_truth:
        tp = sum(1 for row in ground_truth.values() if row["label"] == "TP")
        fp = sum(1 for row in ground_truth.values() if row["label"] == "FP")
        tn = sum(1 for row in ground_truth.values() if row["label"] == "TN")
        fn = sum(1 for row in ground_truth.values() if row["label"] == "FN")

        tpr       = tp / (tp + fn)   if (tp + fn) > 0 else 0.0
        tnr       = tn / (tn + fp)   if (tn + fp) > 0 else 0.0
        fpr       = fp / (fp + tn)   if (fp + tn) > 0 else 0.0
        precision = tp / (tp + fp)   if (tp + fp) > 0 else 0.0

        print(f"\n{'=' * 70}")
        print(f"📐 Confusion Matrix (from ground_truth.csv)")
        print(f"   TP (caught real failures)   : {tp:>3}")
        print(f"   FP (false alarms)           : {fp:>3}")
        print(f"   TN (correctly cleared)      : {tn:>3}")
        print(f"   FN (missed real failures)   : {fn:>3}")
        print(f"\n📈 Checker Performance Metrics")
        print(f"   TPR  (Recall)      : {tpr:.1%}  ← of real failures, how many caught?")
        print(f"   TNR  (Specificity) : {tnr:.1%}  ← of real passes, how many cleared?")
        print(f"   FPR               : {fpr:.1%}  ← false alarm rate")
        print(f"   Precision         : {precision:.1%}  ← of flagged, how many were real?")

        print(f"\n💡 Interpretation")
        if tpr == 1.0:
            print(f"   ✅ TPR=100% — checker caught every real failure")
        elif tpr >= 0.8:
            print(f"   ✅ TPR={tpr:.0%} — checker catches most real failures")
        else:
            print(f"   ⚠️  TPR={tpr:.0%} — checker misses too many real failures")

        if tnr >= 0.8:
            print(f"   ✅ TNR={tnr:.0%} — checker rarely raises false alarms")
        else:
            print(f"   ⚠️  TNR={tnr:.0%} — checker raises too many false alarms (high FP)")
    print()


if __name__ == "__main__":
    main()
