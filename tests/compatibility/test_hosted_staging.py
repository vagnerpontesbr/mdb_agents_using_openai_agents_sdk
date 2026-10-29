"""Ensure the upload staging helper excludes environment and stale files."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class HostedStagingTests(unittest.TestCase):
    def stage(self, output, *extra):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts/prepare_hosted_invoice.py"),
             "--output", str(output), *extra], capture_output=True, text=True,
        )

    def test_source_allowlist_and_existing_destination_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "stage"
            self.assertEqual(self.stage(output).returncode, 0)
            files = {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()}
            expected = {"pyproject.toml", "uv.lock", "agent.yaml"}
            expected.update(p.relative_to(ROOT / "compatibility/openai_engine_adapter").as_posix()
                            for p in (ROOT / "compatibility/openai_engine_adapter/src").rglob("*.py"))
            self.assertEqual(files, expected)
            (output / ".env").write_text("SYNTHETIC_SECRET=not-a-real-key\n")
            self.assertNotEqual(self.stage(output).returncode, 0)

    def test_unverified_interpreter_is_not_extracted(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "python.tar.gz"
            archive.write_bytes(b"unverified artifact")
            output = Path(tmp) / "stage"
            result = self.stage(output, "--python-archive", str(archive))
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((output / ".runtime-python").exists())
            self.assertFalse((output / ".python-version").exists())


if __name__ == "__main__":
    unittest.main()
