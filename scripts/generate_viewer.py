"""
generate_viewer.py — Reads the latest results JSON and generates a
self-contained HTML viewer for ergonomic browsing of queries and responses.

Usage:
    uv run python scripts/generate_viewer.py
    uv run python scripts/generate_viewer.py results/results_20260411_183535.json
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
RESULTS_DIR = ROOT / "results"


def get_results_file() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    # Pick the latest results file
    files = sorted(RESULTS_DIR.glob("results_*.json"))
    if not files:
        raise FileNotFoundError("No results JSON found in results/")
    return files[-1]


def generate_html(data: dict) -> str:
    meta = data["metadata"]
    results = data["results"]

    cards = ""
    for r in results:
        status_badge = (
            '<span class="badge success">✅ Success</span>'
            if r["status"] == "success"
            else '<span class="badge error">❌ Error</span>'
        )
        response_html = (
            r["response"]
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        # Support both legacy (category) and new (dimensions) formats
        if "dimensions" in r and r["dimensions"]:
            dims = r["dimensions"]
            category     = dims.get("cuisine_type") or dims.get("meal_type") or "General"
            dim_badges   = "".join(
                f'<span class="dim-badge">{k.replace("_", " ").title()}: {v}</span>'
                for k, v in dims.items() if k not in ("realistic", "note") and v
            )
            sub_line     = f'<div class="dimensions">{dim_badges}</div>'
        else:
            category   = r.get("category", "General")
            sub_line   = f'<div class="failure-mode">🎯 {r.get("failure_mode_tested", "")}</div>'

        cards += f"""
        <div class="card" data-category="{category}">
            <div class="card-header">
                <div class="card-meta">
                    <span class="id">#{r['id']}</span>
                    <span class="category">{category}</span>
                    {status_badge}
                    <span class="duration">{r['duration_ms']}ms</span>
                </div>
                <div class="query">{r['query']}</div>
                {sub_line}
            </div>
            <div class="response"><pre>{response_html}</pre></div>
        </div>
        """

    # Build filter categories
    cats = []
    for r in results:
        if "dimensions" in r and r["dimensions"]:
            dims = r["dimensions"]
            cats.append(dims.get("cuisine_type") or dims.get("meal_type") or "General")
        else:
            cats.append(r.get("category", "General"))

    categories = sorted(set(cats))
    filter_buttons = '<button class="filter-btn active" onclick="filterCards(\'all\', this)">All</button>'
    for cat in categories:
        filter_buttons += f'<button class="filter-btn" onclick="filterCards(\'{cat}\', this)">{cat}</button>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VP Recipe Agent — Eval Results</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f5f5f0; color: #1a1a1a; }}

  header {{ background: #1a1a1a; color: white; padding: 24px 32px; }}
  header h1 {{ font-size: 1.5rem; margin-bottom: 6px; }}
  .meta-bar {{ display: flex; gap: 20px; font-size: 0.85rem; color: #aaa; flex-wrap: wrap; }}
  .meta-bar span b {{ color: #fff; }}

  .filters {{ background: white; padding: 16px 32px; border-bottom: 1px solid #e0e0e0;
              display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }}
  .filters label {{ font-size: 0.8rem; color: #666; margin-right: 4px; }}
  .filter-btn {{ padding: 6px 14px; border: 1px solid #ddd; border-radius: 20px;
                 background: white; cursor: pointer; font-size: 0.8rem; transition: all 0.2s; }}
  .filter-btn:hover {{ background: #f0f0f0; }}
  .filter-btn.active {{ background: #1a1a1a; color: white; border-color: #1a1a1a; }}

  .container {{ max-width: 960px; margin: 0 auto; padding: 24px 16px; }}

  .card {{ background: white; border-radius: 10px; margin-bottom: 16px;
           box-shadow: 0 1px 4px rgba(0,0,0,0.08); overflow: hidden; }}
  .card-header {{ padding: 16px 20px; border-bottom: 1px solid #f0f0f0; cursor: pointer;
                  user-select: none; }}
  .card-header:hover {{ background: #fafafa; }}
  .card-meta {{ display: flex; gap: 10px; align-items: center; margin-bottom: 8px; flex-wrap: wrap; }}
  .id {{ font-weight: 700; color: #666; font-size: 0.85rem; }}
  .category {{ background: #e8f0fe; color: #1a56db; padding: 2px 10px;
               border-radius: 12px; font-size: 0.75rem; font-weight: 600; }}
  .duration {{ font-size: 0.75rem; color: #999; margin-left: auto; }}
  .badge {{ padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }}
  .badge.success {{ background: #d1fae5; color: #065f46; }}
  .badge.error   {{ background: #fee2e2; color: #991b1b; }}
  .query {{ font-size: 1rem; font-weight: 600; color: #111; margin-bottom: 4px; }}
  .failure-mode {{ font-size: 0.78rem; color: #888; }}

  .response {{ padding: 0; max-height: 0; overflow: hidden; transition: max-height 0.3s ease; }}
  .response.open {{ max-height: 2000px; padding: 16px 20px; }}
  .response pre {{ white-space: pre-wrap; font-family: inherit; font-size: 0.9rem;
                   line-height: 1.65; color: #333; }}

  .dimensions {{ display: flex; gap: 6px; flex-wrap: wrap; margin-top: 6px; }}
  .dim-badge {{ background: #fef3c7; color: #92400e; padding: 2px 8px;
                border-radius: 10px; font-size: 0.72rem; font-weight: 600; }}
  #no-results {{ text-align: center; padding: 60px; color: #999; display: none; }}
</style>
</head>
<body>

<header>
  <h1>🍳 VP Recipe Agent — Eval Results</h1>
  <div class="meta-bar">
    <span>🕐 <b>{meta['timestamp']}</b></span>
    <span>🤖 Model: <b>{meta['model']}</b></span>
    <span>📋 Total: <b>{meta['total']}</b></span>
    <span>✅ Success: <b>{meta['success']}</b></span>
    <span>❌ Errors: <b>{meta['errors']}</b></span>
  </div>
</header>

<div class="filters">
  <label>Filter:</label>
  {filter_buttons}
</div>

<div class="container">
  {cards}
  <div id="no-results">No results for this category.</div>
</div>

<script>
  // Toggle response visibility
  document.querySelectorAll('.card-header').forEach(header => {{
    header.addEventListener('click', () => {{
      const resp = header.nextElementSibling;
      resp.classList.toggle('open');
    }});
  }});

  // Open first card by default
  const first = document.querySelector('.response');
  if (first) first.classList.add('open');

  // Category filter
  function filterCards(category, btn) {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    let visible = 0;
    document.querySelectorAll('.card').forEach(card => {{
      const match = category === 'all' || card.dataset.category === category;
      card.style.display = match ? '' : 'none';
      if (match) visible++;
    }});
    document.getElementById('no-results').style.display = visible === 0 ? 'block' : 'none';
  }}
</script>
</body>
</html>"""


def main():
    results_file = get_results_file()
    print(f"📂 Loading: {results_file}")

    data = json.loads(results_file.read_text(encoding="utf-8"))
    html = generate_html(data)

    output_file = results_file.with_suffix(".html")
    output_file.write_text(html, encoding="utf-8")
    print(f"✅ Viewer saved: {output_file}")
    print(f"   Open in browser: file://{output_file.resolve()}")


if __name__ == "__main__":
    main()
