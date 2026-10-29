"""Negative controls for synthetic PDF page-provenance acceptance."""

import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "pdf_probe", Path(__file__).resolve().parents[2] / "scripts/check_docling_pdf.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class PdfEvidenceTests(unittest.TestCase):
    def document(self):
        return {"pages": {"1": {}, "2": {}}, "texts": [
            {"text": "Check the optical cable before restarting the router.", "prov": [{"page_no": 1}]},
            {"text": "Open a support ticket if the red light remains on.", "prov": [{"page_no": 2}]},
        ]}

    def test_expected_pages_pass(self):
        self.assertTrue(probe.validate_document(self.document())["pass"])

    def test_correct_text_on_wrong_page_fails(self):
        document = self.document()
        document["texts"][0]["prov"] = [{"page_no": 2}]
        self.assertFalse(probe.validate_document(document)["pass"])

    def test_missing_or_ambiguous_provenance_fails(self):
        for provenance in ([], [{"page_no": 1}, {"page_no": 2}]):
            with self.subTest(provenance=provenance):
                document = self.document()
                document["texts"][0]["prov"] = provenance
                self.assertFalse(probe.validate_document(document)["pass"])

    def test_missing_text_or_page_fails(self):
        document = self.document()
        document["texts"].pop()
        self.assertFalse(probe.validate_document(document)["pass"])
        document = self.document()
        document["pages"].pop("2")
        self.assertFalse(probe.validate_document(document)["pass"])


if __name__ == "__main__":
    unittest.main()
