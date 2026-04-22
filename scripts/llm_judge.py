"""
llm_judge.py — LLM-as-Judge evaluator for VP Substitution Agent

Sends each bot response through Claude using judge_prompt.txt
and scores it on 4 criteria: DIETARY, RATIO, ALTERNATIVES, FORMAT

Usage:
    uv run python scripts/llm_judge.py

Output:
    results/judge_results.json   — per-response scores + reasons
    results/judge_vs_human.csv   — judge scores vs human ground truth
"""

import csv
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

import anthropic
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

MODEL      = "claude-opus-4-5"
MAX_TOKENS = 512

JUDGE_PROMPT_FILE  = ROOT / "prompts" / "judge_prompt.txt"
RESULTS_FILE       = ROOT / "results" / "results_20260419_150510.json"
QUERIES_CSV        = ROOT / "data" / "substitution_queries.csv"
GROUND_TRUTH_CSV   = ROOT / "data" / "ground_truth.csv"
RESULTS_DIR        = ROOT / "results"

CRITERIA = ["DIETARY", "RATIO", "ALTERNATIVES", "FORMAT"]


# ── Helpers ───────────────────────────────────────────────────────────────────
def load_judge_prompt() -> str:
    return JUDGE_PROMPT_FILE.read_text(encoding="utf-8").strip()


def load_results() -> list[dict]:
    data = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
    return data["results"]


def load_queries() -> dict:
    """Return a dict keyed by id for fast lookup."""
    with open(QUERIES_CSV, newline="", encoding="utf-8") as f:
        return {row["id"]: row for row in csv.DictReader(f)}


def load_ground_truth() -> dict:
    """Return a dict keyed by id — human label (PASS/FAIL) for each response."""
    gt = {}
    with open(GROUND_TRUTH_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            # Ground truth uses 'label' column — TN/TP/FP/FN
            # PASS = TN or TP (response is correct), FAIL = FP or FN (response flagged)
            label = row.get("label", "").strip().upper()
            gt[row["id"]] = "PASS" if label in ("TN", "TP") else "FAIL"
    return gt


def extract_original_ingredient(response: str) -> str:
    """Extract original ingredient from the '## Substituting X' heading."""
    match = re.search(r"##\s+Substituting\s+(.+?)(?:\s+in\s+|\s+for\s+|$)", response, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return "unknown ingredient"


def build_judge_input(prompt_template: str, query: str, dietary: str,
                      original: str, response: str) -> str:
    """Fill in the judge prompt template with actual values."""
    return (
        prompt_template
        .replace("{query}", query)
        .replace("{dietary_restriction}", dietary if dietary and dietary != "None" else "None specified")
        .replace("{original_ingredient}", original)
        .replace("{response}", response)
    )


def call_judge(client: anthropic.Anthropic, judge_input: str) -> tuple[str, float]:
    """Send the filled judge prompt to Claude and return raw text + duration."""
    start = time.time()
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": judge_input}],
    )
    duration_ms = round((time.time() - start) * 1000)
    return message.content[0].text, duration_ms


def parse_judge_output(text: str) -> dict:
    """
    Parse Claude's response into structured scores.

    Expected format:
        Criteria 1 DIETARY: PASS or FAIL — reason
        Criteria 2 RATIO: PASS or FAIL — reason
        Criteria 3 ALTERNATIVES: PASS or FAIL — reason
        Criteria 4 FORMAT: PASS or FAIL — reason
        Overall: PASS or FAIL
        Overall reason: ...
    """
    scores = {}

    # Parse each criterion
    for criterion in CRITERIA:
        pattern = rf"(?:Criteria\s+\d+\s+)?{criterion}[:\s]+?(PASS|FAIL)[^\n]*?(?:—|-)?\s*(.*)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            scores[criterion] = {
                "result": match.group(1).upper(),
                "reason": match.group(2).strip(),
            }
        else:
            scores[criterion] = {"result": "UNKNOWN", "reason": "Could not parse"}

    # Parse overall
    overall_match = re.search(r"Overall:\s*(PASS|FAIL)", text, re.IGNORECASE)
    reason_match  = re.search(r"Overall reason:\s*(.+)", text, re.IGNORECASE)

    scores["overall"] = {
        "result": overall_match.group(1).upper() if overall_match else "UNKNOWN",
        "reason": reason_match.group(1).strip() if reason_match else "Could not parse",
    }

    return scores


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY not set. Add it to your .env file.")

    client         = anthropic.Anthropic(api_key=api_key)
    judge_prompt   = load_judge_prompt()
    results        = load_results()
    queries        = load_queries()
    ground_truth   = load_ground_truth()

    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    judge_results = []
    total = len(results)

    print(f"\n⚖️  VP Substitution Agent — LLM-as-Judge")
    print(f"   Model   : {MODEL}")
    print(f"   Responses: {total}")
    print(f"   Criteria : {', '.join(CRITERIA)}\n")

    for i, result in enumerate(results, 1):
        rid      = result["id"]
        query    = result["query"]
        response = result["response"]

        # Get dietary restriction from queries CSV
        query_row = queries.get(rid, {})
        dietary   = query_row.get("dietary_restriction", "None")

        # Extract original ingredient from response heading
        original = extract_original_ingredient(response)

        print(f"[{i:02d}/{total}] ID {rid} — {query[:55]}...")
        print(f"         Original ingredient: {original} | Dietary: {dietary}")

        try:
            judge_input = build_judge_input(judge_prompt, query, dietary, original, response)
            raw_output, duration_ms = call_judge(client, judge_input)
            scores = parse_judge_output(raw_output)
            status = "success"
        except Exception as e:
            raw_output  = f"ERROR: {e}"
            scores      = {}
            duration_ms = 0
            status      = "error"

        overall = scores.get("overall", {}).get("result", "UNKNOWN")
        human   = ground_truth.get(rid, "UNKNOWN")
        agree   = "✅ AGREE" if overall == human else "❌ DISAGREE"

        print(f"         Judge: {overall} | Human: {human} | {agree} | {duration_ms}ms\n")

        judge_results.append({
            "id":           rid,
            "query":        query,
            "dietary":      dietary,
            "original":     original,
            "status":       status,
            "duration_ms":  duration_ms,
            "scores":       scores,
            "human_label":  human,
            "agree":        overall == human,
            "raw_output":   raw_output,
        })

    # ── Compute summary metrics ──────────────────────────────────────────────
    total_scored   = sum(1 for r in judge_results if r["status"] == "success")
    total_agree    = sum(1 for r in judge_results if r.get("agree"))
    agreement_rate = round(total_agree / total_scored * 100, 1) if total_scored else 0

    output = {
        "metadata": {
            "timestamp":      timestamp,
            "model":          MODEL,
            "total":          total,
            "scored":         total_scored,
            "agree":          total_agree,
            "disagree":       total_scored - total_agree,
            "agreement_rate": f"{agreement_rate}%",
        },
        "results": judge_results,
    }

    # ── Save judge_results.json ──────────────────────────────────────────────
    judge_file = RESULTS_DIR / f"judge_results_{timestamp}.json"
    judge_file.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Save judge_vs_human.csv ──────────────────────────────────────────────
    csv_file = RESULTS_DIR / "judge_vs_human.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "query", "dietary", "original",
                         "DIETARY", "RATIO", "ALTERNATIVES", "FORMAT",
                         "judge_overall", "human_label", "agree"])
        for r in judge_results:
            scores = r.get("scores", {})
            writer.writerow([
                r["id"], r["query"], r["dietary"], r["original"],
                scores.get("DIETARY",      {}).get("result", ""),
                scores.get("RATIO",        {}).get("result", ""),
                scores.get("ALTERNATIVES", {}).get("result", ""),
                scores.get("FORMAT",       {}).get("result", ""),
                scores.get("overall",      {}).get("result", ""),
                r["human_label"],
                "YES" if r.get("agree") else "NO",
            ])

    # ── Print summary ────────────────────────────────────────────────────────
    print(f"\n{'='*55}")
    print(f"  Judge Agreement Rate : {agreement_rate}% ({total_agree}/{total_scored})")
    print(f"  Disagreements        : {total_scored - total_agree}")
    print(f"{'='*55}")
    print(f"\n✅ Results saved to:")
    print(f"   {judge_file}")
    print(f"   {csv_file}")


if __name__ == "__main__":
    main()
