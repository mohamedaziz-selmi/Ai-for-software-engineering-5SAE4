"""Draws the report's charts from the stored scores (no plotting library needed):
- RAFT candidates on the hand-written validation set (raft/results/scores_prompts.json) -> docs/images/raft_validation.svg
- Base vs RAFT 2a on the final test in the real app (eval/results/assistant_final-*.json) -> docs/images/rag_vs_raft_final.svg

  .venv\\Scripts\\python.exe scripts\\make_charts.py
"""

from __future__ import annotations

import json
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1]
SCORES = MODULE / "raft" / "results" / "scores_prompts.json"
OUT = MODULE / "docs" / "images" / "raft_validation.svg"
NAMES = {"base": "Base model", "run1": "RAFT run 1", "run2a": "RAFT run 2a", "run2b": "RAFT run 2b"}
SERIES = [("All 28 questions", "#3b5b92", lambda s: (s["correct"], s["n"])),
          ("Scope questions", "#7a9a3a", lambda s: tuple(int(x) for x in s["by_type"].get("scope", "0/8").split("/")))]


def main() -> None:
    scores = json.loads(SCORES.read_text(encoding="utf-8"))
    models = [m for m in NAMES if m in scores]
    w, h, left, top, bottom = 160 * len(models) + 120, 330, 70, 40, 70
    plot_h = h - top - bottom
    bar_w, gap = 44, 12
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="Segoe UI, sans-serif" font-size="12">',
             f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
             f'<text x="{left}" y="22" font-size="14" font-weight="bold" fill="#222">Hand-written validation set: answers correct (verified)</text>']
    for pct in (0, 25, 50, 75, 100):
        y = top + plot_h * (1 - pct / 100)
        parts.append(f'<line x1="{left}" y1="{y:.0f}" x2="{w - 20}" y2="{y:.0f}" stroke="#e3e3e3"/>')
        parts.append(f'<text x="{left - 8}" y="{y + 4:.0f}" text-anchor="end" fill="#666">{pct}%</text>')
    for i, model in enumerate(models):
        x0 = left + 30 + i * 160
        for j, (label, color, get) in enumerate(SERIES):
            ok, n = get(scores[model])
            frac = ok / n if n else 0
            bh, x = plot_h * frac, x0 + j * (bar_w + gap)
            parts.append(f'<rect x="{x}" y="{top + plot_h - bh:.0f}" width="{bar_w}" height="{bh:.0f}" fill="{color}"><title>{label}: {ok}/{n}</title></rect>')
            parts.append(f'<text x="{x + bar_w / 2:.0f}" y="{top + plot_h - bh - 6:.0f}" text-anchor="middle" fill="#222">{ok}/{n}</text>')
        harmful = len(scores[model]["harmful"])
        parts.append(f'<text x="{x0 + bar_w + gap / 2:.0f}" y="{top + plot_h + 20}" text-anchor="middle" fill="#222">{NAMES[model]}</text>')
        parts.append(f'<text x="{x0 + bar_w + gap / 2:.0f}" y="{top + plot_h + 36}" text-anchor="middle" fill="{"#b03030" if harmful else "#666"}">{harmful} harmful</text>')
    for j, (label, color, _) in enumerate(SERIES):
        lx = left + j * 170
        parts.append(f'<rect x="{lx}" y="{h - 18}" width="12" height="12" fill="{color}"/><text x="{lx + 18}" y="{h - 8}" fill="#222">{label}</text>')
    parts.append("</svg>")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"{OUT.relative_to(MODULE)}: {', '.join(NAMES[m] for m in models)}")


FINAL = [("base", "Base + RAG", "#3b5b92"), ("raft2a", "RAFT 2a", "#7a9a3a")]
METRICS = [("Correct", "keyword_correct_answerable"), ("Right section cited", "answered_with_gold_section_citation"),
           ("Says 'not in docs'", "abstained_when_unsupported"), ("Scope verdict", "scope_verdict_ok")]


def final_chart() -> None:
    """Grouped bars: each metric as a share, labelled with the raw count."""
    summaries = {}
    for key, _, _ in FINAL:
        path = MODULE / "eval" / "results" / f"assistant_final-{key}.json"
        summaries[key] = json.loads(path.read_text(encoding="utf-8"))["summary"]
    w, h, left, top, bottom = 150 * len(METRICS) + 110, 320, 70, 40, 64
    plot_h, bar_w, gap = h - top - bottom, 44, 10
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="Segoe UI, sans-serif" font-size="12">',
             f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
             f'<text x="{left}" y="22" font-size="14" font-weight="bold" fill="#222">Final test in the real app (33 questions, fallback off)</text>']
    for pct in (0, 25, 50, 75, 100):
        y = top + plot_h * (1 - pct / 100)
        parts.append(f'<line x1="{left}" y1="{y:.0f}" x2="{w - 20}" y2="{y:.0f}" stroke="#e3e3e3"/>')
        parts.append(f'<text x="{left - 8}" y="{y + 4:.0f}" text-anchor="end" fill="#666">{pct}%</text>')
    for i, (label, field) in enumerate(METRICS):
        x0 = left + 25 + i * 150
        for j, (key, _, color) in enumerate(FINAL):
            ok, n = (int(x) for x in str(summaries[key][field]).split("/"))
            bh, x = plot_h * (ok / n if n else 0), x0 + j * (bar_w + gap)
            parts.append(f'<rect x="{x}" y="{top + plot_h - bh:.0f}" width="{bar_w}" height="{bh:.0f}" fill="{color}"><title>{label}: {ok}/{n}</title></rect>')
            parts.append(f'<text x="{x + bar_w / 2:.0f}" y="{top + plot_h - bh - 6:.0f}" text-anchor="middle" fill="#222">{ok}/{n}</text>')
        parts.append(f'<text x="{x0 + bar_w + gap / 2:.0f}" y="{top + plot_h + 20}" text-anchor="middle" fill="#222">{label}</text>')
    for j, (_, name, color) in enumerate(FINAL):
        lx = left + j * 140
        parts.append(f'<rect x="{lx}" y="{h - 18}" width="12" height="12" fill="{color}"/><text x="{lx + 18}" y="{h - 8}" fill="#222">{name}</text>')
    parts.append("</svg>")
    out = MODULE / "docs" / "images" / "rag_vs_raft_final.svg"
    out.write_text("\n".join(parts), encoding="utf-8")
    print(f"{out.relative_to(MODULE)}: {', '.join(name for _, name, _ in FINAL)}")


if __name__ == "__main__":
    main()
    final_chart()
