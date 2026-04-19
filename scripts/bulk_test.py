"""
bulk_test.py — Runs all queries in a CSV through the Recipe Suggestion Bot
and writes results to results/results_<timestamp>.json

Usage:
    uv run python scripts/bulk_test.py                              # uses data/substitution_queries.csv
    uv run python scripts/bulk_test.py data/dimension_queries.csv  # custom CSV
"""

import csv
import json
import os
import sys
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

SYSTEM_PROMPT_FILE = ROOT / "prompts" / "system_prompt.txt"
RESULTS_DIR        = ROOT / "results"

# Dimension columns to carry through from dimension_queries.csv
DIMENSION_COLUMNS = ["cuisine_type", "dietary_restriction", "meal_type", "skill_level", "realistic", "note"]


# ── Helpers ───────────────────────────────────────────────────────────────────
def load_system_prompt() -> str:
    return SYSTEM_PROMPT_FILE.read_text(encoding="utf-8").strip()


def load_queries(csv_path: Path) -> list[dict]:
    with open(csv_path, newline="", encoding="utf-8") as f:
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


def build_dimensions(row: dict) -> dict:
    """Extract dimension columns if present in the CSV row."""
    return {col: row[col] for col in DIMENSION_COLUMNS if col in row and row[col]}


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY not set. Add it to your .env file.")

    # Accept optional CSV path argument
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "substitution_queries.csv"
    if not csv_path.is_absolute():
        csv_path = ROOT / csv_path

    client        = anthropic.Anthropic(api_key=api_key)
    system_prompt = load_system_prompt()
    queries       = load_queries(csv_path)

    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = RESULTS_DIR / f"results_{timestamp}.json"

    results = []
    total   = len(queries)

    print(f"\n🔄 VP Substitution Agent — Bulk Test")
    print(f"   Model   : {MODEL}")
    print(f"   CSV     : {csv_path.name}")
    print(f"   Queries : {total}")
    print(f"   Output  : {output_file}\n")

    for i, row in enumerate(queries, 1):
        query = row["query"]
        print(f"[{i:02d}/{total}] {query[:65]}...")

        try:
            response, duration_ms = run_query(client, system_prompt, query)
            status = "success"
        except Exception as e:
            response    = f"ERROR: {e}"
            duration_ms = 0
            status      = "error"

        result = {
            "id":         row["id"],
            "query":      query,
            "dimensions": build_dimensions(row),
            "status":     status,
            "duration_ms": duration_ms,
            "response":   response,
        }

        # Carry over legacy columns if present
        if "category" in row:
            result["category"] = row["category"]
        if "failure_mode_tested" in row:
            result["failure_mode_tested"] = row["failure_mode_tested"]

        results.append(result)
        print(f"         ✅ {duration_ms}ms\n" if status == "success" else f"         ❌ {response}\n")

    output = {
        "metadata": {
            "timestamp": timestamp,
            "model":     MODEL,
            "csv":       csv_path.name,
            "total":     total,
            "success":   sum(1 for r in results if r["status"] == "success"),
            "errors":    sum(1 for r in results if r["status"] == "error"),
        },
        "results": results,
    }

    output_file.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✅ Done! Results saved to: {output_file}")


if __name__ == "__main__":
    main()
