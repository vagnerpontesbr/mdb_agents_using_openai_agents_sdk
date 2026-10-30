"""One isolated PDF job at a time; bounded provider processing ends in staging only."""

import hashlib
import json
import os
import signal
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .knowledge import MAX_CHUNKS, MAX_PAGES, MAX_TEXT, align_chunks, canonical
from .knowledge_search import PROFILE
from .knowledge_voyage import ProviderUnavailable, VoyageKnowledge, vector


def validate_staged(result: dict[str, Any], checksum: str, scanned: bool) -> None:
    if (set(result) != {"checksum", "pages", "chunks", "parser_version", "ocr", "embedding_profile"}
            or result["checksum"] != checksum or result["ocr"] is not scanned
            or result["parser_version"] != "docling-2.143.1"
            or result["embedding_profile"] != PROFILE):
        raise ValueError("Invalid staging provenance")
    pages, chunks = result["pages"], result["chunks"]
    if (not isinstance(pages, list) or not 1 <= len(pages) <= MAX_PAGES
            or any(not isinstance(page, str) or not page.strip() for page in pages)
            or sum(len(page.encode()) for page in pages) > MAX_TEXT
            or not isinstance(chunks, list) or not 1 <= len(chunks) <= MAX_CHUNKS):
        raise ValueError("Staging exceeds document bounds")
    for chunk in chunks:
        if (not isinstance(chunk, dict)
                or set(chunk) != {"text", "pages", "text_sha256", "embedding"}):
            raise ValueError("Invalid staged chunk")
        vector(chunk["embedding"])
        if not isinstance(chunk["text"], str):
            raise ValueError("Invalid staged text")
    aligned = align_chunks(pages, [chunk["text"] for chunk in chunks])
    source_text = " ".join(canonical(page) for page in pages)
    for original, chunk in zip(aligned, chunks, strict=True):
        if (original.text not in source_text
                or chunk["text"] != original.text or chunk["text_sha256"] != original.text_sha256
                or chunk["pages"] != list(original.pages)
                or any(type(page) is not int for page in chunk["pages"])):
            raise ValueError("Staging provenance does not match the source")


def process_pdf(pdf: bytes, scanned: bool, root: Path, voyage: VoyageKnowledge) -> dict[str, Any]:
    """Call the separately locked CPU runtime, never import Docling into the app."""
    with tempfile.TemporaryDirectory(prefix="telecom-ingestion-") as directory:
        source, output = Path(directory) / "source.pdf", Path(directory) / "pages.json"
        source.write_bytes(pdf)
        command = ["uv", "run", "--project", str(root / "compatibility/ingestion-runtime"),
                   "--frozen", "python", str(root / "scripts/extract_knowledge_pdf.py"),
                   str(source), "--output", str(output), "--allow-model-downloads"]
        if scanned:
            command.append("--scanned")
        # The outer deadline also kills descendants if conversion fails to shut down.
        with subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              start_new_session=True) as child:
            try:
                if child.wait(timeout=270) != 0:
                    raise ValueError("PDF extraction failed")
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
                raise ValueError("PDF extraction exceeded its deadline") from None
        extracted = json.loads(output.read_text())
    checksum = hashlib.sha256(pdf).hexdigest()
    if (extracted.get("contract") != "telecom-pdf-pages-v1"
            or extracted.get("checksum") != checksum or extracted.get("ocr") is not scanned):
        raise ValueError("Extraction integrity failed")
    embedded = voyage.embed_pages(extracted["pages"])
    result = {"checksum": checksum, "pages": extracted["pages"], "ocr": scanned,
              "parser_version": extracted["parser_version"], "embedding_profile": PROFILE,
              "chunks": [{"text": item.source.text, "pages": list(item.source.pages),
                          "text_sha256": item.source.text_sha256, "embedding": list(item.embedding)}
                         for item in embedded]}
    validate_staged(result, checksum, scanned)
    return result


def failure_category(error: Exception) -> str:
    if isinstance(error, ProviderUnavailable):
        return "provider_failure"
    return "invalid_document" if isinstance(error, ValueError) else "worker_failure"
