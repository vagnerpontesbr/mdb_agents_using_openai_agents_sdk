"""Isolated CPU Docling worker: PDF to bounded page text, without publication."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

MAX_BYTES = 5_000_000
MAX_PAGES = 10
MAX_TEXT = 60_000


def convert(path: Path, output: Path, scanned: bool) -> None:
    from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractCliOcrOptions, OcrMode
    from docling.document_converter import DocumentConverter, PdfFormatOption
    options = PdfPipelineOptions(
        accelerator_options=AcceleratorOptions(device=AcceleratorDevice.CPU, num_threads=2),
        do_ocr=scanned, do_table_structure=True,
        ocr_options=TesseractCliOcrOptions(lang=["eng"], mode=OcrMode.FULL_PAGE))
    result = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(
        pipeline_options=options)}).convert(path, max_num_pages=MAX_PAGES, max_file_size=MAX_BYTES)
    if result.status.value != "success":
        raise ValueError("Incomplete PDF conversion")
    document = result.document.model_dump(mode="json")
    count = len(document.get("pages", {}))
    if not 1 <= count <= MAX_PAGES or document.get("tables"):
        # Flattening tables without a validated representation could change a procedure.
        raise ValueError("Page bound or unvalidated table layout")
    pages = [[] for _ in range(count)]
    for item in document.get("texts", []):
        provenance = {p.get("page_no") for p in item.get("prov", [])}
        if len(provenance) != 1:
            raise ValueError("Ambiguous source page")
        page = next(iter(provenance))
        if type(page) is not int or not 1 <= page <= count:
            raise ValueError("Invalid source page")
        pages[page - 1].append(item.get("text", ""))
    text = ["\n".join(page) for page in pages]
    if not all(p.strip() for p in text) or sum(map(len, text)) > MAX_TEXT:
        raise ValueError("Empty page or oversized extraction")
    output.write_text(json.dumps({"contract": "telecom-pdf-pages-v1", "pages": text,
        "checksum": hashlib.sha256(path.read_bytes()).hexdigest(),
        "parser_version": "docling-2.143.1", "ocr": scanned}, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scanned", action="store_true")
    parser.add_argument("--allow-model-downloads", action="store_true")
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.allow_model_downloads:
        parser.error("Explicit --allow-model-downloads is required for Docling")
    if (not args.pdf.is_file() or not 1 <= args.pdf.stat().st_size <= MAX_BYTES
            or args.pdf.read_bytes()[:5] != b"%PDF-"):
        parser.error("Expected a PDF within the 5 MB limit")
    if args.output.exists():
        parser.error("Output must be a new file")
    if args.child:
        convert(args.pdf, args.output, args.scanned)
        return 0
    with tempfile.TemporaryDirectory(prefix="telecom-pdf-") as temp:
        copied = Path(temp) / "source.pdf"
        copied.write_bytes(args.pdf.read_bytes())
        extracted = Path(temp) / "pages.json"
        command = [sys.executable, __file__, str(copied), "--output", str(extracted),
                   "--child", "--allow-model-downloads"]
        if args.scanned:
            command.append("--scanned")
        try:
            subprocess.run(command, timeout=240, check=True, capture_output=True)
            # Exclusive creation preserves an existing artifact on failure/retry.
            with args.output.open("x") as target:
                target.write(extracted.read_text())
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            print("PDF extraction failed or exceeded the 240-second limit; details suppressed")
            return 1
    print("PDF pages extracted; no source was published")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
