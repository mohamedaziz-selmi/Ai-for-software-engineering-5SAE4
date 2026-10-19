"""Builds the whole documentation as ONE PDF (for Blackboard): docs/AI_Assistant_Delivery_Review_Mohamed_Aziz_Selmi.pdf.

Rebuilds docs/REPORT.md first (scripts/build_report.py), then renders it with headless Chrome (or Edge): a cover, the
contents with page numbers, every section and appendix, every screenshot and diagram embedded, PDF bookmarks. Fonts are
the module's own (Hanken Grotesk, Source Serif 4, JetBrains Mono from frontend/node_modules, embedded), so the PDF looks
the same on any PC. Two passes: the second fills in the page numbers the first one measured.

  .venv\\Scripts\\python.exe scripts\\build_report_pdf.py
"""

from __future__ import annotations

import base64
import html
import io
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from markdown_it import MarkdownIt
from pypdf import PdfReader, PdfWriter

import build_report
from capture_screens import BROWSERS, Page

MODULE = Path(__file__).resolve().parents[1]
DOCS = MODULE / "docs"
OUT = DOCS / "AI_Assistant_Delivery_Review_Mohamed_Aziz_Selmi.pdf"
TITLE, AUTHOR = "AI Assistant & Delivery Review", "Mohamed Aziz Selmi"
FONTS = MODULE / "frontend" / "node_modules" / "@fontsource-variable"
FONT_CSS = ["hanken-grotesk/index.css", "hanken-grotesk/wght-italic.css", "source-serif-4/opsz.css",
            "source-serif-4/opsz-italic.css", "jetbrains-mono/index.css", "jetbrains-mono/wght-italic.css"]
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml"}


def font_faces() -> str:
    """The latin and latin-ext @font-face rules of the module's fonts, each font file embedded as a data URI."""
    rules = []
    for name in FONT_CSS:
        css = FONTS / name
        if not css.is_file():
            print(f"font missing (system font used instead): {css}")
            continue
        for label, rule in re.findall(r"/\*\s*([\w-]+)\s*\*/\s*(@font-face\s*\{.*?\})", css.read_text(encoding="utf-8"), re.S):
            if not re.search(r"-latin-(ext-)?[a-z]+-(normal|italic)$", label):
                continue
            src = re.search(r"url\(\./files/([^)]+)\)", rule).group(1)
            data = base64.b64encode((css.parent / "files" / src).read_bytes()).decode()
            rules.append(rule.replace(f"url(./files/{src})", f"url(data:font/woff2;base64,{data})"))
    return "\n".join(rules)


def markdown_html(markdown: str) -> tuple[str, list[tuple[str, str]]]:
    """HTML of the report body, with GitHub-style ids on headings; returns the level-2 headings (id, text)."""
    md = MarkdownIt("commonmark", {"html": True}).enable(["table", "strikethrough"])
    tokens = md.parse(markdown)
    used, sections = set(), []
    for i, token in enumerate(tokens):
        if token.type == "heading_open":
            text = tokens[i + 1].content
            base = build_report.slug(text) or "section"
            slug, n = base, 1
            while slug in used:
                n += 1
                slug = f"{base}-{n}"
            used.add(slug)
            token.attrSet("id", slug)
            if token.tag == "h2":
                sections.append((slug, re.sub(r"[`*_]", "", text)))
    return md.renderer.render(tokens, md.options, {}), sections


def embed_images(body: str) -> str:
    """Figures with captions; images as data URIs; the report's diagrams inline, so they use the report's fonts."""
    body = re.sub(r"<p>(<img [^>]+>)</p>\s*<p><em>(.*?)</em></p>", r"<figure>\1<figcaption>\2</figcaption></figure>", body, flags=re.S)
    body = re.sub(r"<p>(<img [^>]+>)</p>", r"<figure>\1</figure>", body)

    def image(match: re.Match) -> str:
        tag, src = match.group(0), html.unescape(match.group(1))
        path = DOCS / src
        if not path.is_file():
            raise FileNotFoundError(f"image missing: {src}")
        if path.name.startswith("diagram-"):
            svg = re.sub(r"<\?xml[^>]*\?>", "", path.read_text(encoding="utf-8"))
            return svg.replace("<svg ", '<svg class="diagram" ', 1)
        data = base64.b64encode(path.read_bytes()).decode()
        return tag.replace(match.group(1), f"data:{MIME[path.suffix.lower()]};base64,{data}")

    return re.sub(r'<img src="([^"]+)"[^>]*>', image, body)


def fit_tables(body: str) -> str:
    """Tables never widen the page (Chrome would then shrink every page): cell text may break after "_" and "/",
    and tables of 7 or more columns use the compact style."""
    def table(match: re.Match) -> str:
        text = re.sub(r">([^<]+)<", lambda m: ">" + m.group(1).replace("_", "_<wbr>").replace("/", "/<wbr>") + "<", match.group(0))
        columns = len(re.findall(r"<th[ >]", text.split("</tr>", 1)[0]))
        return text.replace("<table>", '<table class="dense">', 1) if columns >= 7 else text
    return re.sub(r"<table>.*?</table>", table, body, flags=re.S)


def body_html(markdown: str) -> tuple[str, list[tuple[str, str]]]:
    body, sections = markdown_html(markdown)
    return fit_tables(embed_images(body)), sections


def toc_html(sections: list[tuple[str, str]], pages: dict[str, int]) -> str:
    rows = []
    for slug, text in sections:
        appendix = text.startswith("Appendix")
        number, _, name = text.partition(": ") if appendix else text.partition(". ")
        label = f"{number}" if appendix else f"{number}."
        if appendix and not any(r.startswith('<li class="gap"') for r in rows):
            rows.append('<li class="gap" aria-hidden="true"></li>')
        rows.append(f'<li><a href="#{slug}"><span class="no">{html.escape(label)}</span><span class="name">{html.escape(name or text)}</span>'
                    f'<span class="leader"></span><span class="pg">{pages.get(slug, "00")}</span></a></li>')
    return "\n".join(rows)


def page_html(body: str, intro: str, sections: list[tuple[str, str]], pages: dict[str, int], fonts: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{html.escape(TITLE)}: project report</title>
<meta name="author" content="{AUTHOR}">
<style>
{fonts}
{CSS}
</style></head>
<body>
<section class="cover">
  <div class="cover-mark" aria-hidden="true"></div>
  <div class="cover-top">
    <div class="eyebrow">ESPRIT · IA for Software Engineering · A.U. 2026–2027</div>
    <div class="cover-title">AI Assistant<br>&amp; Delivery Review</div>
    <div class="cover-sub">Project report and full documentation of a module of the Cerebro freelancer–client platform</div>
  </div>
  <div class="cover-bottom">
    <dl>
      <dt>Author</dt><dd>{AUTHOR}</dd>
      <dt>Date</dt><dd>19 October 2026</dd>
      <dt>Built with</dt><dd>Claude Code (Claude Opus 5.5)</dd>
      <dt>Code</dt><dd>module_assistant_delivery/ · github.com/mohamedaziz-selmi/freelance-platform (private)</dd>
    </dl>
    <div class="cover-note">{intro}</div>
  </div>
</section>
<section class="toc">
  <div class="toc-title">Contents</div>
  <ol>{toc_html(sections, pages)}</ol>
</section>
<main>
{body}
</main>
</body></html>"""


CSS = r"""
:root {
  --ink: oklch(0.21 0.014 255); --ink-2: oklch(0.4 0.014 255); --ink-3: oklch(0.5 0.013 255);
  --line: oklch(0.888 0.006 250); --line-strong: oklch(0.78 0.009 250); --sunken: oklch(0.962 0.004 250);
  --accent: oklch(0.89 0.19 127); --accent-ink: oklch(0.47 0.13 135); --accent-wash: oklch(0.982 0.03 127);
  --serif: "Source Serif 4 Variable", Georgia, serif;
  --sans: "Hanken Grotesk Variable", "Segoe UI", sans-serif;
  --mono: "JetBrains Mono Variable", Consolas, monospace;
}
@page {
  size: A4; margin: 16mm 17mm 17mm 17mm;
  @bottom-left { content: "AI Assistant & Delivery Review · Mohamed Aziz Selmi"; font-family: "Hanken Grotesk Variable", "Segoe UI", sans-serif; font-size: 7.4pt; color: #6a7078; }
  @bottom-right { content: counter(page) " / " counter(pages); font-family: "Hanken Grotesk Variable", "Segoe UI", sans-serif; font-size: 7.4pt; color: #6a7078; }
}
@page :first { margin: 0; @bottom-left { content: none; } @bottom-right { content: none; } }
html { font-size: 9.7pt; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; background: #fff; color: var(--ink); font-family: var(--serif); line-height: 1.46; font-optical-sizing: auto; hyphens: auto; }

/* Cover */
.cover { height: 297mm; box-sizing: border-box; padding: 34mm 22mm 24mm 30mm; display: flex; flex-direction: column;
  justify-content: space-between; position: relative; break-after: page; font-family: var(--sans); }
.cover-mark { position: absolute; left: 0; top: 0; bottom: 0; width: 9mm; background: var(--accent); }
.eyebrow { font-size: 9pt; font-weight: 600; letter-spacing: 0.02em; color: var(--accent-ink); margin-bottom: 9mm; }
.cover-title { font-size: 40pt; line-height: 1.02; font-weight: 750; letter-spacing: -0.025em; color: var(--ink); }
.cover-sub { margin-top: 7mm; max-width: 125mm; font-family: var(--serif); font-size: 13.5pt; line-height: 1.35; color: var(--ink-2); }
.cover dl { display: grid; grid-template-columns: 26mm 1fr; gap: 2.2mm 4mm; margin: 0 0 9mm; font-size: 9.4pt; }
.cover dt { color: var(--ink-3); font-weight: 500; }
.cover dd { margin: 0; color: var(--ink); font-weight: 600; }
.cover-note { border-top: 0.8pt solid var(--line-strong); padding-top: 4mm; max-width: 150mm; font-family: var(--serif);
  font-size: 9.6pt; color: var(--ink-2); }
.cover-note p { margin: 0; }

/* Contents */
.toc { break-after: page; font-family: var(--sans); }
.toc-title { font-size: 20pt; font-weight: 700; letter-spacing: -0.015em; margin: 4mm 0 8mm; padding-top: 3mm; border-top: 2.4pt solid var(--accent); width: 100%; }
.toc ol { list-style: none; margin: 0; padding: 0; }
.toc li a { display: flex; align-items: baseline; gap: 2.5mm; padding: 1.55mm 0; color: var(--ink); text-decoration: none; font-size: 10.4pt; }
.toc .no { flex: 0 0 auto; min-width: 7mm; color: var(--ink-3); font-variant-numeric: tabular-nums; }
.toc .name { flex: 0 1 auto; font-weight: 550; }
.toc .leader { flex: 1 1 auto; border-bottom: 0.9pt dotted var(--line-strong); transform: translateY(-1mm); }
.toc .pg { flex: 0 0 auto; font-variant-numeric: tabular-nums; color: var(--ink-2); }
.toc li.gap { height: 5mm; }

/* Body */
main > h2:first-child { break-before: page; }
h2, h3, h4, h5, h6 { font-family: var(--sans); color: var(--ink); line-height: 1.22; break-after: avoid; }
h2 { font-size: 17pt; font-weight: 720; letter-spacing: -0.012em; margin: 11mm 0 4mm; padding-top: 3mm; border-top: 2.2pt solid var(--accent); }
h2[id^="appendix-"] { break-before: page; margin-top: 0; }
main > h2:first-child { margin-top: 0; }
h3 { font-size: 12.4pt; font-weight: 680; margin: 7mm 0 2.2mm; }
h4 { font-size: 10.6pt; font-weight: 680; margin: 5.5mm 0 1.8mm; }
h5 { font-size: 9.9pt; font-weight: 660; margin: 4.5mm 0 1.4mm; }
h6 { font-size: 9.5pt; font-weight: 640; margin: 4mm 0 1.2mm; color: var(--ink-2); }
p { margin: 0 0 2.5mm; orphans: 3; widows: 3; }
ul, ol { margin: 0 0 2.6mm; padding-left: 5mm; }
li { margin: 0.7mm 0; }
li > p { margin: 0 0 1.2mm; }
strong { font-weight: 660; }
em { font-style: italic; }
a { color: inherit; text-decoration: underline; text-decoration-color: var(--line-strong); text-underline-offset: 0.18em; }
hr { display: none; }
code, pre { font-variant-ligatures: none; font-feature-settings: "liga" 0, "calt" 0; }  /* verbatim: "===" stays three signs */
code { font-family: var(--mono); font-size: 0.84em; background: var(--sunken); padding: 0.08em 0.3em; border-radius: 2.5px; overflow-wrap: anywhere; }
pre { font-family: var(--mono); font-size: 7.3pt; line-height: 1.45; background: oklch(0.977 0.003 250); border: 0.6pt solid var(--line);
  border-radius: 3px; padding: 2.6mm 3.2mm; margin: 1.6mm 0 3.4mm; white-space: pre-wrap; overflow-wrap: anywhere; hyphens: none; }
pre code { background: none; padding: 0; font-size: inherit; border-radius: 0; }
blockquote { margin: 2mm 0 3.2mm; padding: 2mm 4mm; border-left: 2.4pt solid var(--accent); background: var(--accent-wash); color: var(--ink-2); }
blockquote p:last-child { margin-bottom: 0; }

table { width: 100%; border-collapse: collapse; margin: 2mm 0 4.2mm; font-family: var(--sans); font-size: 8.25pt; line-height: 1.36; hyphens: none; }
thead { display: table-header-group; }
th { text-align: left; font-weight: 650; background: var(--sunken); border-bottom: 0.8pt solid var(--line-strong); }
th, td { padding: 1.35mm 2mm; vertical-align: top; border-bottom: 0.5pt solid var(--line); overflow-wrap: break-word; }
tr { break-inside: avoid; }
td code, th code { font-size: 0.9em; }
table.dense { font-size: 6.5pt; line-height: 1.3; }
table.dense th, table.dense td { padding: 0.8mm 1mm; }

figure { margin: 3mm 0 5.5mm; break-inside: avoid; text-align: center; }
figure img { max-width: 100%; max-height: 246mm; border: 0.6pt solid var(--line); border-radius: 3px; }
figure svg.diagram { width: 100%; height: auto; display: block; }
figcaption { font-family: var(--sans); font-size: 8.1pt; line-height: 1.38; color: var(--ink-3); margin-top: 1.8mm; text-align: left; }
td img { width: 100%; height: auto; border: 0.6pt solid var(--line); border-radius: 2px; }
td > img:only-child { display: block; }
"""


def print_pdf(page: Page, url: str) -> bytes:
    page.send("Page.navigate", url=url)
    page.wait("document.readyState === 'complete'", 60)
    page.js("document.fonts.ready.then(() => true)")
    page.wait("[...document.images].every(i => i.complete)", 60)
    time.sleep(0.5)
    result = page.send("Page.printToPDF", preferCSSPageSize=True, printBackground=True, generateDocumentOutline=True,
                       generateTaggedPDF=True, transferMode="ReturnAsStream")
    chunks = []
    while True:
        part = page.send("IO.read", handle=result["stream"], size=1 << 20)
        chunks.append(base64.b64decode(part["data"]) if part.get("base64Encoded") else part["data"].encode("latin-1"))
        if part.get("eof"):
            break
    page.send("IO.close", handle=result["stream"])
    return b"".join(chunks)


def section_pages(pdf: bytes, sections: list[tuple[str, str]]) -> dict[str, int]:
    """Page of each section (1 = the cover), from the PDF's bookmarks, else from the page text."""
    reader = PdfReader(io.BytesIO(pdf))
    marks = []

    def walk(items) -> None:
        for item in items:
            if isinstance(item, list):
                walk(item)
            else:
                marks.append((" ".join(item.title.split()), reader.get_destination_page_number(item) + 1))

    walk(reader.outline)
    found, i = {}, 0
    for slug, text in sections:
        want = " ".join(text.split())
        while i < len(marks) and marks[i][0] != want:
            i += 1
        if i < len(marks):
            found[slug] = marks[i][1]
            i += 1
    if len(found) < len(sections):  # no bookmarks: search the page text, in order
        texts = [" ".join((p.extract_text() or "").split()) for p in reader.pages]
        start = 2
        for slug, text in sections:
            if slug not in found:
                want = " ".join(text.split())
                found[slug] = next((n + 1 for n in range(start, len(texts)) if want in texts[n]), 0)
            start = max(start, found[slug] - 1)
    return found


def main() -> None:
    build_report.main()
    report = (DOCS / "REPORT.md").read_text(encoding="utf-8")
    head, _, rest = report.partition("\n---\n")  # title, intro and contents: replaced by the cover and the contents page
    intro = re.search(r"\n\n(.+?)\n\n\*\*Contents\*\*", head, re.S).group(1)
    body, sections = body_html(rest)
    intro = re.sub(r"\A.*?Selmi\.\s*Built with Claude Code \(Claude Opus 5\.5\); the", "The", intro, flags=re.S)  # the cover says the rest
    intro_html = MarkdownIt("commonmark").render(intro)
    fonts = font_faces()
    browser = next(b for b in BROWSERS if Path(b).is_file())
    work = Path(tempfile.mkdtemp(prefix="ad-report-pdf-"))
    proc = subprocess.Popen([browser, "--headless=new", "--remote-debugging-port=9339", "--remote-allow-origins=*",
                             f"--user-data-dir={work / 'profile'}", "--no-first-run", "--no-default-browser-check",
                             "--force-color-profile=srgb", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        page = Page(9339)
        pages: dict[str, int] = {}
        for attempt in range(1, 4):
            source = work / f"report-{attempt}.html"
            source.write_text(page_html(body, intro_html, sections, pages, fonts), encoding="utf-8")
            pdf = print_pdf(page, source.as_uri())
            measured = section_pages(pdf, sections)
            if measured == pages:
                break
            pages = measured
        else:
            raise RuntimeError("page numbers did not settle")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(work, ignore_errors=True)
    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(pdf)))
    writer.add_metadata({"/Title": f"{TITLE}: project report", "/Author": AUTHOR,
                         "/Subject": "ESPRIT IA for Software Engineering, module documentation",
                         "/Creator": "scripts/build_report_pdf.py (headless Chrome)"})
    with OUT.open("wb") as f:
        writer.write(f)
    count = len(PdfReader(OUT).pages)
    print(f"wrote {OUT.relative_to(MODULE)}: {count} pages, {OUT.stat().st_size / 1e6:.1f} MB, passes: {attempt}")
    for slug, text in sections:
        print(f"  {pages[slug]:>4}  {text}")


if __name__ == "__main__":
    main()
