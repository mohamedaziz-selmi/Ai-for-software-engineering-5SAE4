"""Draws the report's three diagrams (architecture, assistant, delivery review) as SVG files in docs/images/.

Colours are the module's OKLCH tokens (frontend/src/assistant-workspace.css), converted to hex so the files open in any
viewer. Text uses Hanken Grotesk when the page provides it (the PDF build does), else Segoe UI.
Usage: .venv\\Scripts\\python.exe scripts\\make_report_diagrams.py
"""

from __future__ import annotations

import math
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parents[1] / "docs" / "images"
FONT = "'Hanken Grotesk Variable', 'Hanken Grotesk', 'Segoe UI', system-ui, sans-serif"


def oklch(l: float, c: float, h: float) -> str:
    a, b = c * math.cos(math.radians(h)), c * math.sin(math.radians(h))
    l_, m_, s_ = (l + 0.3963377774 * a + 0.2158037573 * b) ** 3, (l - 0.1055613458 * a - 0.0638541728 * b) ** 3, \
        (l - 0.0894841775 * a - 1.2914855480 * b) ** 3
    rgb = (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
           -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
           -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)
    gamma = [12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055 for v in rgb]
    return "#" + "".join(f"{round(min(1, max(0, v)) * 255):02x}" for v in gamma)


TEXT, TEXT_2, TEXT_3 = oklch(0.21, 0.014, 255), oklch(0.4, 0.014, 255), oklch(0.5, 0.013, 255)
LINE, LINE_STRONG, SUNKEN = oklch(0.888, 0.006, 250), oklch(0.78, 0.009, 250), oklch(0.955, 0.005, 250)
ACCENT_FILL, ACCENT_EDGE = oklch(0.965, 0.065, 127), oklch(0.47, 0.13, 135)


class Svg:
    def __init__(self, name: str, width: int, height: int, title: str) -> None:
        self.name, self.width, self.height, self.title, self.parts = name, width, height, title, []

    def box(self, x, y, w, h, title, sub=None, kind="node"):
        fill, stroke = {"node": ("#ffffff", LINE_STRONG), "accent": (ACCENT_FILL, ACCENT_EDGE), "muted": (SUNKEN, LINE_STRONG)}[kind]
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{fill}" stroke="{stroke}" stroke-width="1.3"/>')
        self._label(x + w / 2, y + h / 2, title, sub)

    def store(self, x, y, w, h, title, sub=None):
        ry = 7
        self.parts.append(f'<path d="M{x},{y + ry} a{w / 2},{ry} 0 0,1 {w},0 v{h - 2 * ry} a{w / 2},{ry} 0 0,1 {-w},0 z" fill="#ffffff" '
                          f'stroke="{LINE_STRONG}" stroke-width="1.3"/>')
        self.parts.append(f'<path d="M{x},{y + ry} a{w / 2},{ry} 0 0,0 {w},0" fill="none" stroke="{LINE_STRONG}" stroke-width="1.3"/>')
        self._label(x + w / 2, y + h / 2 + 4, title, sub)

    def diamond(self, cx, cy, w, h, lines):
        pts = f"{cx},{cy - h / 2} {cx + w / 2},{cy} {cx},{cy + h / 2} {cx - w / 2},{cy}"
        self.parts.append(f'<polygon points="{pts}" fill="#ffffff" stroke="{LINE_STRONG}" stroke-width="1.3"/>')
        top = cy - (len(lines) - 1) * 9 + 5
        for i, line in enumerate(lines):
            self.parts.append(f'<text x="{cx}" y="{top + i * 18}" text-anchor="middle" font-size="14" font-weight="600" fill="{TEXT}">{escape(line)}</text>')

    def group(self, x, y, w, h, label):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="none" stroke="{LINE_STRONG}" stroke-width="1.2" stroke-dasharray="6 5"/>')
        self.parts.append(f'<text x="{x + 16}" y="{y + 22}" font-size="12.5" font-weight="600" fill="{TEXT_3}">{escape(label)}</text>')

    def _label(self, cx, cy, title, sub):
        if sub:
            self.parts.append(f'<text x="{cx}" y="{cy - 3}" text-anchor="middle" font-size="15" font-weight="650" fill="{TEXT}">{escape(title)}</text>')
            self.parts.append(f'<text x="{cx}" y="{cy + 15}" text-anchor="middle" font-size="12.5" fill="{TEXT_3}">{escape(sub)}</text>')
        else:
            self.parts.append(f'<text x="{cx}" y="{cy + 5}" text-anchor="middle" font-size="15" font-weight="650" fill="{TEXT}">{escape(title)}</text>')

    def arrow(self, points, dashed=False):
        d = "M" + " L".join(f"{x},{y}" for x, y in points)
        dash = ' stroke-dasharray="5 4"' if dashed else ""
        self.parts.append(f'<path d="{d}" fill="none" stroke="{TEXT_2}" stroke-width="1.4"{dash} marker-end="url(#{self.name}-head)"/>')

    def note(self, x, y, lines, anchor="middle", on_line=False):
        """Edge label; on_line puts it on a white chip so the line it sits on stays readable."""
        for i, line in enumerate(lines):
            ty = y + i * 15
            if on_line:
                w = len(line) * 6.3 + 12
                left = x - w / 2 if anchor == "middle" else x if anchor == "start" else x - w
                self.parts.append(f'<rect x="{left:.1f}" y="{ty - 12}" width="{w:.1f}" height="17" rx="4" fill="#ffffff"/>')
            self.parts.append(f'<text x="{x}" y="{ty}" text-anchor="{anchor}" font-size="12" fill="{TEXT_2}">{escape(line)}</text>')

    def write(self) -> Path:
        head = (f'<marker id="{self.name}-head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{TEXT_2}"/></marker>')
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.width} {self.height}" width="{self.width}" height="{self.height}" '
               f'font-family="{FONT}" role="img" aria-label="{escape(self.title)}">\n<title>{escape(self.title)}</title>\n<defs>{head}</defs>\n'
               + "\n".join(self.parts) + "\n</svg>\n")
        path = OUT / f"{self.name}.svg"
        path.write_text(svg, encoding="utf-8")
        return path


def architecture() -> Path:
    s = Svg("diagram-architecture", 1000, 440, "Architecture: the module behind the platform's API gateway")
    s.box(16, 170, 118, 54, "Browser")
    s.box(190, 170, 170, 54, "API gateway", ":8080")
    s.box(190, 350, 170, 60, "Control center", ":8090, my microservice")
    s.box(450, 66, 214, 60, "This module", ":8003, FastAPI + React", "accent")
    s.box(450, 280, 214, 54, "Platform facade", ":8081")
    s.box(744, 8, 240, 58, "Private Ollama :11435", "Base or RAFT, one loaded at a time")
    s.box(744, 80, 240, 58, "Groq free tier", "gpt-oss-120b")
    s.store(744, 152, 240, 64, "SQLite + Chroma", "documents, passages, reviews")
    s.box(744, 250, 240, 54, "Template dashboard", ":8766")
    s.box(744, 320, 240, 58, "Existing services", ":8000–8002, retrieval, sentiment, BI")
    s.arrow([(134, 197), (188, 197)])
    s.arrow([(360, 186), (425, 186), (425, 96), (448, 96)])
    s.arrow([(360, 208), (425, 208), (425, 307), (448, 307)])
    s.note(425, 146, ["/assistant, /api/ai"], on_line=True)
    s.note(425, 262, ["everything else"], on_line=True)
    for y_from, y_to in ((82, 37), (96, 109), (110, 184)):
        s.arrow([(664, y_from), (704, y_from), (704, y_to), (742, y_to)])
    s.arrow([(664, 298), (704, 298), (704, 277), (742, 277)])
    s.arrow([(664, 316), (704, 316), (704, 349), (742, 349)])
    s.arrow([(222, 350), (222, 226)], dashed=True)
    s.arrow([(328, 224), (328, 348)], dashed=True)
    s.note(214, 282, ["starts and stops", "every module"], anchor="end")
    s.note(336, 282, ["the bubble on", "every page"], anchor="start")
    s.arrow([(744, 420), (782, 420)])
    s.note(790, 424, ["request"], anchor="start")
    s.arrow([(862, 420), (900, 420)], dashed=True)
    s.note(908, 424, ["control"], anchor="start")
    return s.write()


def assistant() -> Path:
    s = Svg("diagram-assistant", 1000, 382, "Project assistant: retrieve, generate, verify")
    s.box(16, 16, 150, 60, "Question", "freelancer or client")
    s.box(226, 16, 250, 60, "Top 5 passages", "this project only, e5 + Chroma")
    s.box(536, 16, 250, 60, "Prompt + passages", "personal data masked")
    s.arrow([(166, 46), (224, 46)])
    s.arrow([(476, 46), (534, 46)])
    s.arrow([(661, 76), (661, 118)])
    s.group(16, 120, 968, 120, "Generate: a JSON answer with exact quotes")
    s.box(40, 156, 260, 60, "Chosen local model", "Base + RAG (default) or RAFT")
    s.box(370, 156, 260, 60, "The other local model", "local backup")
    s.box(700, 156, 260, 60, "Groq free tier", "gpt-oss-120b, hosted fallback")
    s.arrow([(300, 186), (368, 186)], dashed=True)
    s.arrow([(630, 186), (698, 186)], dashed=True)
    s.note(334, 178, ["fails"])
    s.note(664, 178, ["fails too"])
    s.arrow([(500, 240), (500, 268)])
    s.diamond(500, 316, 230, 92, ["Quote found", "in its passage?"])
    s.box(700, 287, 284, 58, "Answer + verified citation", "the quote is checked in code", "accent")
    s.box(16, 287, 284, 58, "“Not in the documents”", "no citation, no guess", "muted")
    s.arrow([(615, 316), (698, 316)])
    s.arrow([(385, 316), (302, 316)])
    s.note(656, 308, ["yes"])
    s.note(344, 308, ["no"])
    return s.write()


def review() -> Path:
    s = Svg("diagram-review", 1000, 340, "Delivery review: judge each requirement, verify every quote")
    s.box(16, 16, 200, 58, "Milestone folder", "code and text files")
    s.box(16, 96, 200, 58, "Requirements", "from the contract (REQ-, NN-)")
    s.box(266, 56, 210, 58, "4 relevant excerpts", "per requirement")
    s.box(526, 56, 230, 58, "gpt-oss-120b", "verdict + findings with quotes")
    s.arrow([(216, 45), (241, 45), (241, 85), (264, 85)])
    s.arrow([(216, 125), (241, 125), (241, 85), (264, 85)])
    s.arrow([(476, 85), (524, 85)])
    s.arrow([(641, 114), (641, 166)])
    s.diamond(641, 214, 210, 92, ["Quote in that file", "at those lines?"])
    s.box(790, 185, 194, 58, "Kept", "with file, lines and quote", "accent")
    s.box(790, 270, 194, 58, "Report", "the client accepts or dismisses")
    s.box(300, 185, 200, 58, "Dropped", "counted, never shown", "muted")
    s.arrow([(746, 214), (788, 214)])
    s.arrow([(536, 214), (502, 214)])
    s.arrow([(887, 243), (887, 268)])
    s.note(767, 206, ["yes"])
    s.note(519, 206, ["no"])
    return s.write()


if __name__ == "__main__":
    for make in (architecture, assistant, review):
        print("wrote", make().relative_to(OUT.parents[1]))
