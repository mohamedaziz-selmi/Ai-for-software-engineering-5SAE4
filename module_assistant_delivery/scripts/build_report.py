"""Assembles docs/REPORT.md, the single project report, from its parts, so it never drifts from the real files:
the prompts are inserted verbatim from backend/app/llm/prompts/, the RAFT run 2 results and the professor guide from
docs/report/, the last test run from docs/report/test_run.txt, and the working log from docs/AI_USAGE_LOG.md (owner's
messages verbatim, left unchanged), with the structured tuning prompts of docs/report/tuning_prompts.md placed in the
parts where their steps happened. The module's other documents follow, unchanged, as appendices B to G, so the report
is the whole documentation; scripts/build_report_pdf.py turns it into one PDF.

  .venv\\Scripts\\python.exe scripts\\build_report.py
"""

from __future__ import annotations

import re
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1]
DOCS = MODULE / "docs"
PROMPTS = MODULE / "backend" / "app" / "llm" / "prompts"


def read(path: Path, missing: str = "") -> str:
    return path.read_text(encoding="utf-8").strip() if path.exists() else missing


def headings(markdown: str):
    """(index, line) of every heading line, skipping fenced code (a "# comment" in a code block is not a heading)."""
    fenced = False
    for i, line in enumerate(markdown.split("\n")):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced and re.match(r"#{1,6} ", line):
            yield i, line


def demote(markdown: str, levels: int = 2) -> str:
    """Headings of an appended document go under the appendix heading (# -> ###)."""
    lines = markdown.split("\n")
    for i, line in headings(markdown):
        hashes = len(line) - len(line.lstrip("#"))
        lines[i] = "#" * min(6, hashes + levels) + line[hashes:]
    return "\n".join(lines)


# Where each structured tuning prompt (docs/report/tuning_prompts.md) goes in the working log: in the part where
# its step happened, before the given line of that part (None = at the end of the part).
PLACEMENT = {
    "A.1": ("part 5:", None), "A.2": ("part 5:", None),
    **{f"A.{n}": ("part 16:", "- **Request declined") for n in range(3, 10)},
}


def tuning_entries() -> dict[str, tuple[str, str, str]]:
    text = read(DOCS / "report" / "tuning_prompts.md")
    found = re.findall(r"^### (A\.\d) (.+?)\n\n```text\n(.*?)\n```\n\n(\*\*Result:\*\*.*?)(?=\n\n---|\Z)", text, re.S | re.M)
    return {key: (title, prompt, result) for key, title, prompt, result in found}


def working_log() -> str:
    """The usage log, unchanged, with each structured tuning prompt placed in the part where its step happened.
    The log's empty entry template is left out of the report."""
    text = read(DOCS / "AI_USAGE_LOG.md").replace("\r\n", "\n")
    text = re.sub(r"\n## Entry template\n.*?\n---\n", "\n", text, count=1, flags=re.S)
    lines = text.split("\n")
    entries = tuning_entries()
    assert set(entries) == set(PLACEMENT), sorted(entries)
    inserts: dict[int, list[str]] = {}
    for key in sorted(entries, key=lambda k: int(k.split(".")[1])):
        heading, before = PLACEMENT[key]
        start = next(i for i, line in enumerate(lines) if line.startswith("#### ") and heading in line)
        end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith(("### ", "#### "))), len(lines))
        at = next(i for i in range(start, end) if lines[i].startswith(before)) if before else end
        title, prompt, result = entries[key]
        block = [f"- **Structured tuning prompt (reconstructed from this step): {title}**", "", "  ```text"]
        block += [f"  {line}" if line else "" for line in prompt.split("\n")] + ["  ```", "", f"  {result}", ""]
        inserts.setdefault(at, []).extend(block)
    out = []
    for i, line in enumerate(lines + [""]):
        out.extend(inserts.get(i, []))
        if i < len(lines):
            out.append(line)
    return "\n".join(out)


def document(path: Path, levels: int) -> str:
    """Another document of the module, unchanged, without its title line, its headings moved under the appendix."""
    body = read(path).replace("\r\n", "\n")
    body = re.sub(r"\A# .*\n+", "", body)
    return demote(body, levels)


# Appendices B to G: the module's other documents. (heading, [(sub-heading or None, file), ...])
EVAL = MODULE / "eval" / "results"
APPENDICES = [
    ("Appendix B: setup, run and test", [("B.1 Setup on a new machine, run, commands (`README.md`)", MODULE / "README.md"),
                                          ("B.2 Run-and-test guide (`docs/RUN_AND_TEST.md`)", DOCS / "RUN_AND_TEST.md")]),
    ("Appendix C: demo kit and test files", [(None, MODULE / "demo" / "README.md")]),
    ("Appendix D: module specification", [(None, DOCS / "MODULE_SPEC.md")]),
    ("Appendix E: repository audit", [(None, DOCS / "AUDIT.md")]),
    ("Appendix F: evaluation records", [
        ("F.1 Model selection", EVAL / "model_selection.md"), ("F.2 Retrieval", EVAL / "retrieval_comparison.md"),
        ("F.3 Hosted review model", EVAL / "hosted_review_summary.md"), ("F.4 Review accuracy and stability", EVAL / "review_stability.md"),
        ("F.5 RAFT run 1", EVAL / "raft_findings.md"), ("F.6 Base vs RAFT run 1", EVAL / "base_vs_raft.md"),
        ("F.7 Final test, base model", EVAL / "assistant_final-base.md"), ("F.8 Final test, RAFT 2a", EVAL / "assistant_final-raft2a.md"),
    ]),
    ("Appendix G: instructions given to Claude Code", [(None, MODULE / "CLAUDE.md")]),
]


def appendices() -> str:
    out = []
    for heading, docs in APPENDICES:
        out += ["---", "", f"## {heading}", ""]
        for sub, path in docs:
            source = path.relative_to(MODULE).as_posix()
            if sub:
                out += [f"### {sub}", "", f"Source: `{source}`, included as is.", "", document(path, 2), ""]
            else:
                out += [f"Source: `{source}`, included as is.", "", document(path, 1), ""]
    return "\n".join(out).rstrip() + "\n"


def slug(heading: str) -> str:
    """GitHub's anchor for a heading."""
    text = re.sub(r"[`*_]", "", heading).strip().lower()
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


def contents(text: str) -> str:
    rows = [line[3:].strip() for _, line in headings(text) if line.startswith("## ")]
    return "\n".join(f"- [{re.sub(r'`', '', h)}](#{slug(h)})" for h in rows)


def main() -> None:
    text = read(DOCS / "report" / "REPORT.main.md").replace("\r\n", "\n")
    parts = {
        "<!-- PROMPT:assistant -->": read(PROMPTS / "assistant_answer.v1.md"),
        "<!-- PROMPT:review -->": read(PROMPTS / "review_judge.v2.md"),
        "<!-- RESULTS:before-after -->": read(DOCS / "report" / "before_after.md"),
        "<!-- RESULTS:raft2 -->": read(DOCS / "report" / "raft2_results.md", "*RAFT run 2 results: pending.*"),
        "<!-- RESULTS:summary -->": read(DOCS / "report" / "summary_extra.md"),
        "<!-- GUIDE:professor -->": read(DOCS / "report" / "professor_guide.md", "*Guide: pending.*"),
        "<!-- TEST:run -->": read(DOCS / "report" / "test_run.txt"),
        "<!-- APPENDIX:usage-log -->": demote(working_log()) + "\n\n" + appendices(),
    }
    for marker, content in parts.items():
        assert marker in text, marker
        text = text.replace(marker, content.replace("\r\n", "\n"))
    text = re.sub(r"<!-- AFTER:[\w-]+ -->", "*pending*", text)  # measurements not taken yet
    text = text.replace("<!-- CONTENTS -->", contents(text))
    (DOCS / "REPORT.md").write_text(text + "\n", encoding="utf-8")
    missing = [p for p in re.findall(r"\]\((images/[^)]+)\)", text) if not (DOCS / p).exists()]
    print(f"docs/REPORT.md written ({len(text.splitlines())} lines)" + (f"; missing images: {missing}" if missing else ""))


if __name__ == "__main__":
    main()
