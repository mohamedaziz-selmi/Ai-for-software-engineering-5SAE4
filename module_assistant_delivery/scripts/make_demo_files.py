"""Write the demo kit's binary example files (synthetic, fictional content): a DOCX change request, and the files that the
upload checks must refuse (image-only PDF, CSV, non-UTF-8 text, a deliverable with an image, a deliverable with a file over
200 KB). The text examples are plain files in demo/. Usage: .venv\\Scripts\\python.exe scripts\\make_demo_files.py
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont

DEMO = Path(__file__).resolve().parents[1] / "demo"
FONT = Path(r"C:\Windows\Fonts\georgia.ttf")


def font(size: int):
    return ImageFont.truetype(str(FONT), size) if FONT.is_file() else ImageFont.load_default()


# ----------------------------------------------------------------------------- DOCX (accepted)
def _p(text: str, bold: bool = False, size: int = 22) -> str:
    props = f"<w:rPr>{'<w:b/>' if bold else ''}<w:sz w:val=\"{size}\"/></w:rPr>"
    return f"<w:p><w:r>{props}<w:t xml:space=\"preserve\">{escape(text)}</w:t></w:r></w:p>"


def _table(rows: list[tuple[str, str]]) -> str:
    border = "".join(f"<w:{s} w:val=\"single\" w:sz=\"4\" w:color=\"999999\"/>" for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
    cells = "".join("<w:tr>" + "".join(f"<w:tc><w:p><w:r><w:t xml:space=\"preserve\">{escape(c)}</w:t></w:r></w:p></w:tc>" for c in row) + "</w:tr>"
                    for row in rows)
    return f"<w:tbl><w:tblPr><w:tblW w:w=\"0\" w:type=\"auto\"/><w:tblBorders>{border}</w:tblBorders></w:tblPr>{cells}</w:tbl>"


def change_request_docx(path: Path) -> None:
    body = "".join([
        _p("Change request CR-01: SMS pickup reminder", bold=True, size=32),
        _p("Project PRJ-DEMO-001, Atelier Lumière online ordering. Synthetic demonstration document; people and figures are fictional."),
        _p("1. Request", bold=True, size=26),
        _p("Requested by the client in writing on 23 October 2026: send an SMS to the customer 30 minutes before the pickup slot starts."),
        _p("2. Why it is a change request", bold=True, size=26),
        _p("SMS reminders are not listed in section 3.1 of the specification, so section 3.3 (change requests) applies."),
        _p("3. Estimate", bold=True, size=26),
        _p("Sent by the freelancer on 24 October 2026, within the 3 business days required by section 3.3."),
        _table([("Item", "Value"), ("Effort", "3 days"), ("Price", "1,500 TND excluding VAT"),
                ("SMS cost", "Paid by the client directly to the SMS provider"), ("Delivery", "With milestone M3")]),
        _p("4. Decision", bold=True, size=26),
        _p("Approved in writing by the client on 27 October 2026. Work starts on 28 October 2026."),
    ])
    document = ("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">"
                f"<w:body>{body}<w:sectPr/></w:body></w:document>")
    types = ("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
             "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
             "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
             "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
             "<Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>"
             "</Types>")
    rels = ("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
            "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
            "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"word/document.xml\"/>"
            "</Relationships>")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document)


# ----------------------------------------------------------------------------- refused files
def scanned_pdf(path: Path) -> None:
    """A letter that exists only as a picture of text, like a phone scan: no text layer, so the upload is refused."""
    page = Image.new("RGB", (1240, 1754), (246, 244, 238))
    draw = ImageDraw.Draw(page)
    lines = ["Atelier Lumière", "", "Tunis, 24 October 2026", "", "Subject: delivery of the product photos", "",
             "The product photos for the catalogue will be sent on 25 October 2026,",
             "as agreed in decision D-3 of the meeting of 20 October.", "", "Synthetic demonstration document.",
             "", "The operations manager"]
    for i, line in enumerate(lines):
        draw.text((140, 180 + i * 56), line, fill=(40, 40, 46), font=font(34 if i else 46))
    page.rotate(0.7, fillcolor=(246, 244, 238)).save(path, "PDF", resolution=150)


def budget_csv(path: Path) -> None:
    path.write_text("item,amount_tnd\nM1 prototype,3600\nM2 ordering flow,5400\nM3 back-office,5400\nFinal,3600\n", encoding="utf-8")


def windows_1252_text(path: Path) -> None:
    text = ("Notes de l'appel du 20 octobre 2026 (PRJ-DEMO-001, document de démonstration).\r\n"
            "Enregistré avec l'encodage Windows-1252 : les accents ne sont pas de l'UTF-8.\r\n"
            "- Fermeture le dimanche, créneaux de 07:00 à 19:00.\r\n")
    path.write_bytes(text.encode("cp1252"))


def deliverable_with_image(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "README.md").write_text("# M3 mock-up\n\nSynthetic demonstration deliverable: the back-office mock-up as an image.\n", encoding="utf-8")
    image = Image.new("RGB", (960, 600), (250, 250, 252))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 960, 64), fill=(165, 14, 36))
    draw.text((24, 16), "Commandes du jour", fill="white", font=font(28))
    for i in range(6):
        draw.rectangle((24, 96 + i * 72, 936, 152 + i * 72), outline=(210, 210, 216), width=2)
    image.save(folder / "mockup.png")


def deliverable_with_large_file(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "README.md").write_text("# M3 front-end build\n\nSynthetic demonstration deliverable with a bundled vendor file.\n", encoding="utf-8")
    parts = ["/*! vendor bundle, synthetic demo file */"]
    i = 0
    while sum(map(len, parts)) < 260_000:
        parts.append(f"function v{i}(a,b){{return a*{i % 97}+b-{i % 13}}};")
        i += 1
    (folder / "vendor.bundle.js").write_text("".join(parts), encoding="utf-8")


def main() -> None:
    change_request_docx(DEMO / "documents" / "PRJ-DEMO-001_change_request_CR-01.docx")
    refused = DEMO / "rejected"
    (refused / "documents").mkdir(parents=True, exist_ok=True)
    scanned_pdf(refused / "documents" / "PRJ-DEMO-001_scanned_letter.pdf")
    budget_csv(refused / "documents" / "PRJ-DEMO-001_budget.csv")
    windows_1252_text(refused / "documents" / "PRJ-DEMO-001_notes_windows-1252.txt")
    deliverable_with_image(refused / "deliverable_with_image")
    deliverable_with_large_file(refused / "deliverable_with_large_file")
    for p in sorted(DEMO.rglob("*")):
        if p.is_file() and ("rejected" in p.parts or p.suffix == ".docx"):
            print(f"{p.stat().st_size:>8}  {p.relative_to(DEMO)}")


if __name__ == "__main__":
    main()
