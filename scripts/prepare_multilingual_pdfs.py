# /// script
# requires-python = ">=3.14"
# dependencies = ["reportlab==4.4.3"]
# ///
"""Render synthetic source drafts only; no credentials, provider calls or publication."""

import hashlib
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/telecom/governance/multilingual/optical-v1.json"
OUTPUT = ROOT / "output/pdf"


def main():
    fixture = json.loads(SOURCE.read_text())
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest = {"status": fixture["status"], "generator": "reportlab-4.4.3",
                "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(), "files": []}
    body = ParagraphStyle("body", fontName="Helvetica", fontSize=12, leading=18,
                          textColor=colors.HexColor("#18312c"), alignment=TA_LEFT)
    heading = ParagraphStyle("heading", parent=body, fontName="Helvetica-Bold",
                             fontSize=23, leading=29)
    small = ParagraphStyle("small", parent=body, fontSize=10, leading=15)
    for source in fixture["sources"]:
        path = OUTPUT / f"lang2c-optical-{source['language']}.pdf"
        canvas = Canvas(str(path), pagesize=(210 * mm, 297 * mm), invariant=1)
        canvas.setTitle(source["title"])
        canvas.setAuthor("Telecom synthetic demo")
        canvas.setFillColor(colors.HexColor("#00684a"))
        canvas.rect(0, 285 * mm, 210 * mm, 12 * mm, fill=1, stroke=0)
        y = 267 * mm

        def paragraph(text, style=body, gap=14):
            nonlocal y
            p = Paragraph(escape(text), style)
            _, height = p.wrap(166 * mm, y)
            if y - height < 25 * mm:
                raise ValueError("One-page source would overflow")
            p.drawOn(canvas, 22 * mm, y - height)
            y -= height + gap

        paragraph(source["title"], heading)
        paragraph(f"{source['document_id']} | {fixture['version_id']} | {source['language']}", small)
        paragraph(source["notice"], small)
        paragraph(source["scope_text"])
        for index, step in enumerate(source["steps"], 1):
            paragraph(f"{index}. {step}")
        if source.get("translation_of_document"):
            paragraph(f"Source: {source['translation_of_document']} / {fixture['version_id']}", small)
        canvas.setFont("Helvetica", 9)
        canvas.drawString(22 * mm, 16 * mm, "Telecom synthetic demo | 1 / 1")
        canvas.save()
        manifest["files"].append({"path": str(path.relative_to(ROOT)),
                                  "language": source["language"],
                                  "document_id": source["document_id"], "pages": 1,
                                  "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    (OUTPUT / "lang2c-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Prepared three one-page draft PDFs and their checksum manifest; no publication")


if __name__ == "__main__":
    main()
