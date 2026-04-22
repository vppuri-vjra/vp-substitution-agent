"""
bulk_test_ab.py — A/B test two system prompts against the same 20 queries

Version A: prompts/system_prompt.txt    (with worked example)
Version B: prompts/system_prompt_v2.txt (without worked example)

Runs all 20 queries through both prompts and saves labeled result files.

Usage:
    python3 scripts/bulk_test_ab.py

Output:
    results/results_v1_<timestamp>.json  — Version A responses
    results/results_v2_<timestamp>.json  — Version B responses
"""

import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path

import anthropic
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

MODEL      = "claude-opus-4-5"
MAX_TOKENS = 1024

QUERIES_CSV = ROOT / "data" / "substitution_queries.csv"
RESULTS_DIR = ROOT / "results"

VERSIONS = {
    "v1": {
        "label":       "Version A — with worked example",
        "prompt_file": ROOT / "prompts" / "system_prompt.txt",
    },
    "v2": {
        "label":       "Version B — without worked example",
        "prompt_file": ROOT / "prompts" / "system_prompt_v2.txt",
    },
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def load_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def load_queries() -> list[dict]:
    with open(QUERIES_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run_query(client: anthropic.Anthropic, system_prompt: str, query: str) -> tuple[str, float]:
    start = time.time()
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": query}],
    )
    duration_ms = round((time.time() - start) * 1000)
    return message.content[0].text, duration_ms


def run_version(client: anthropic.Anthropic, version_key: str,
                version_info: dict, queries: list[dict],
                timestamp: str) -> Path:
    """Run all queries through one prompt version and save results."""

    system_prompt = load_prompt(version_info["prompt_file"])
    label         = version_info["label"]
    total         = len(queries)
    results       = []

    print(f"\n{'='*55}")
    print(f"  Running {label}")
    print(f"{'='*55}\n")

    for i, row in enumerate(queries, 1):
        query = row["query"]
        print(f"[{i:02d}/{total}] {query[:60]}...")

        try:
            response, duration_ms = run_query(client, system_prompt, query)
            status = "success"
        except Exception as e:
            response    = f"ERROR: {e}"
            duration_ms = 0
            status      = "error"

        results.append({
            "id":          row["id"],
            "query":       query,
            "dimensions": {
                "ingredient_type":    row.get("ingredient_type", ""),
                "cooking_method":     row.get("cooking_method", ""),
                "dietary_restriction": row.get("dietary_restriction", ""),
                "query_clarity":      row.get("query_clarity", ""),
            },
            "status":      status,
            "duration_ms": duration_ms,
            "response":    response,
        })

        print(f"         ✅ {duration_ms}ms\n" if status == "success" else f"         ❌ {response}\n")

    # Save results
    output = {
        "metadata": {
            "timestamp":   timestamp,
            "version":     version_key,
            "label":       label,
            "model":       MODEL,
            "total":       total,
            "success":     sum(1 for r in results if r["status"] == "success"),
            "errors":      sum(1 for r in results if r["status"] == "error"),
        },
        "results": results,
    }

    output_file = RESULTS_DIR / f"results_{version_key}_{timestamp}.json"
    output_file.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Saved: {output_file}\n")
    return output_file


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY not set. Add it to your .env file.")

    client    = anthropic.Anthropic(api_key=api_key)
    queries   = load_queries()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    RESULTS_DIR.mkdir(exist_ok=True)

    print(f"\n🔬 VP Substitution Agent — A/B Prompt Test")
    print(f"   Model    : {MODEL}")
    print(f"   Queries  : {len(queries)}")
    print(f"   Versions : {len(VERSIONS)}")
    print(f"   Variable : Worked example (V1=included, V2=removed)")

    saved_files = {}
    for version_key, version_info in VERSIONS.items():
        saved_files[version_key] = run_version(
            client, version_key, version_info, queries, timestamp
        )

    print(f"\n{'='*55}")
    print(f"  A/B Test Complete")
    print(f"{'='*55}")
    print(f"  Version A results : {saved_files['v1'].name}")
    print(f"  Version B results : {saved_files['v2'].name}")
    print(f"\n  Next step: run llm_judge.py on both files to compare scores")
    print(f"  python3 scripts/llm_judge.py results/{saved_files['v1'].name}")
    print(f"  python3 scripts/llm_judge.py results/{saved_files['v2'].name}")


if __name__ == "__main__":
    main()
