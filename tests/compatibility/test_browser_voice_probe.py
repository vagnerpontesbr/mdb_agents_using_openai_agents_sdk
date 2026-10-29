"""Local browser probe ingress and PCM encoding controls; no provider calls."""
import io
import unittest
import wave

from scripts.serve_voice_engine_probe import valid_request, wav_bytes


class BrowserProbeTests(unittest.TestCase):
    def test_origin_host_and_nonce_are_all_required(self):
        headers = {"Origin": "http://127.0.0.1:8768", "Host": "127.0.0.1:8768",
                   "X-Probe-Nonce": "synthetic-nonce"}
        self.assertTrue(valid_request(headers, origin=headers["Origin"], nonce="synthetic-nonce"))
        for field in headers:
            for value in ("", "https://untrusted.example"):
                changed = {**headers, field: value}
                self.assertFalse(valid_request(changed, origin=headers["Origin"], nonce="synthetic-nonce"))

    def test_pcm_has_explicit_mono_24khz_16bit_wav_contract(self):
        pcm = b"\x01\x00" * 24_000
        with wave.open(io.BytesIO(wav_bytes(pcm)), "rb") as result:
            self.assertEqual((result.getnchannels(), result.getframerate(), result.getsampwidth()),
                             (1, 24_000, 2))
            self.assertEqual(result.readframes(result.getnframes()), pcm)
        for invalid in (b"", b"\x00\x00", b"x"):
            with self.assertRaises(ValueError):
                wav_bytes(invalid)


if __name__ == "__main__":
    unittest.main()
