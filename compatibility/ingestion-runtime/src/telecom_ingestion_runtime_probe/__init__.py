"""CPU contracts for the isolated Phase 0 ingestion dependency graph."""

def check() -> dict:
    from importlib.metadata import version
    import platform
    import torch
    from docling.document_converter import DocumentConverter
    from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
    from docling.datamodel.pipeline_options import PdfPipelineOptions

    options = PdfPipelineOptions(accelerator_options=AcceleratorOptions(
        device=AcceleratorDevice.CPU, num_threads=2))
    tensor = torch.tensor([2, 3], device="cpu") + 1
    assert tensor.tolist() == [3, 4] and tensor.device.type == "cpu"
    assert options.accelerator_options.device == AcceleratorDevice.CPU
    assert DocumentConverter is not None
    return {"scope": "ingestion_dependency_cpu", "python": platform.python_version(),
            "versions": {name: version(name) for name in ("docling", "torch")},
            "device": "cpu", "pdf_conversion": False, "phase0_complete": False}
