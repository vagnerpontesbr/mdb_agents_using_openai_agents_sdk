"""Local token-update safety; no OAuth requests."""

from pathlib import Path
import tempfile
import unittest

from scripts.refresh_engine_token import replace_token, write_env


class TokenRefreshTests(unittest.TestCase):
    def test_preserves_unrelated_configuration(self):
        original = "# comment\nOTHER=unchanged\nAGENT_ENGINE_SERVICE_ACCOUNT_TOKEN=old\n"
        updated = replace_token(original, "new.synthetic-token")
        self.assertEqual(updated, "# comment\nOTHER=unchanged\nAGENT_ENGINE_SERVICE_ACCOUNT_TOKEN=new.synthetic-token\n")

    def test_rejects_duplicate_and_injected_values(self):
        with self.assertRaises(ValueError):
            replace_token("AGENT_ENGINE_SERVICE_ACCOUNT_TOKEN=a\nAGENT_ENGINE_SERVICE_ACCOUNT_TOKEN=b\n", "token")
        for token in ("", "bad\nINJECTED=yes", "bad#comment"):
            with self.assertRaises(ValueError):
                replace_token("OTHER=yes\n", token)

    def test_atomic_private_file_and_symlink_refusal(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / ".env"
            write_env(path, "synthetic")
            self.assertEqual(path.read_text(), "synthetic")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            link = Path(folder) / "link"
            link.symlink_to(path)
            with self.assertRaises(ValueError):
                write_env(link, "changed")
            self.assertEqual(path.read_text(), "synthetic")


if __name__ == "__main__":
    unittest.main()
