"""Verify the CPU ingestion dependency boundary; no model downloads or GPU calls.

This import/tensor smoke check does not establish PDF conversion/OCR quality.
Run with the ingestion candidate requirements on Python 3.14.
"""

from importlib import metadata
import json
from pathlib import Path
import platform
import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = {
        "scope": "docling_cpu_imports",
        "python": platform.python_version(),
        "phase0_complete": False,
        "gpu_used": False,
        "pdf_conversion_verified": False,
    }
    try:
        import torch
        from docling.document_converter import DocumentConverter
        from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
        from docling.datamodel.pipeline_options import PdfPipelineOptions

        options = PdfPipelineOptions(
            accelerator_options=AcceleratorOptions(device=AcceleratorDevice.CPU, num_threads=2)
        )
        tensor = torch.tensor([2, 3], device="cpu") + 1
        passed = (tensor.tolist() == [3, 4] and tensor.device.type == "cpu"
                  and options.accelerator_options.device == AcceleratorDevice.CPU
                  and DocumentConverter is not None)
        report.update(status="pass" if passed else "fail",
                      docling=metadata.version("docling"), torch=metadata.version("torch"),
                      tensor_device=tensor.device.type, pipeline_device=options.accelerator_options.device.value)
    except Exception as exc:
        report.update(status="fail", error_class=type(exc).__name__)
    encoded = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
    print(encoded, end="")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
