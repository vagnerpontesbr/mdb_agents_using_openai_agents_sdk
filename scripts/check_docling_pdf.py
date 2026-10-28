"""Bounded, opt-in Docling CPU conversion of synthetic Phase 0 PDF fixtures.

May download Docling model weights. No cloud inference or customer inputs.
"""

import argparse
from datetime import datetime, timezone
from importlib import metadata
import json
from pathlib import Path
import platform
import subprocess
import sys


def validate_document(document: dict) -> dict:
    expected = {
        1: "Check the optical cable before restarting the router.",
        2: "Open a support ticket if the red light remains on.",
    }
    matches = {}
    for page, phrase in expected.items():
        matches[str(page)] = any(
            phrase in " ".join(item.get("text", "").split())
            and {prov.get("page_no") for prov in item.get("prov", [])} == {page}
            for item in document.get("texts", [])
        )
    return {"expected_text_on_correct_pages": matches,
            "pass": all(matches.values()) and len(document.get("pages", {})) == 2}


def worker(fixture: Path, output: Path) -> None:
    from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractCliOcrOptions, OcrMode
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions(
        accelerator_options=AcceleratorOptions(device=AcceleratorDevice.CPU, num_threads=2),
        do_ocr=fixture.stem == "scanned",
        do_table_structure=True,
        ocr_options=TesseractCliOcrOptions(lang=["eng"], mode=OcrMode.FULL_PAGE),
    )
    converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})
    result = converter.convert(fixture, max_num_pages=2, max_file_size=5_000_000)
    document = result.document.model_dump(mode="json")
    check = validate_document(document)
    check["conversion_status"] = result.status.value
    check["pass"] = check["pass"] and result.status.value == "success"
    output.write_text(json.dumps(check, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-model-downloads", action="store_true")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path, default=Path("artifacts/compatibility/docling-pdf.json"))
    args = parser.parse_args()
    if not args.allow_model_downloads:
        parser.error("Explicit --allow-model-downloads is required for conversion")
    if args.worker:
        worker(args.worker, args.output)
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = {"scope": "synthetic_pdf_cpu_conversion", "phase0_complete": False,
              "time_utc": datetime.now(timezone.utc).isoformat(),
              "python": platform.python_version(), "docling": metadata.version("docling"),
              "torch": metadata.version("torch"), "device": "cpu", "checks": {}}
    for name in ("text", "scanned"):
        result_path = args.output.parent / f"docling-{name}-result.json"
        fixture = Path("artifacts/compatibility/pdf") / f"{name}.pdf"
        if not fixture.exists():
            report["checks"][name] = {"pass": False, "reason": "missing_fixture"}
            continue
        try:
            subprocess.run([sys.executable, __file__, "--allow-model-downloads", "--worker",
                            str(fixture), "--output", str(result_path)],
                           check=True, timeout=240)
            report["checks"][name] = json.loads(result_path.read_text())
        except subprocess.TimeoutExpired:
            report["checks"][name] = {"pass": False, "reason": "240_second_deadline"}
        except subprocess.CalledProcessError:
            report["checks"][name] = {"pass": False, "reason": "conversion_process_failed"}
    report["status"] = "pass" if all(c["pass"] for c in report["checks"].values()) else "fail"
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
