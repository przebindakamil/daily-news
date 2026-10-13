"""Safety tests for encrypting editorial reports before public commits."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import secure_audit as secure

PASSWORD = "correct horse battery staple and five private words"


class ProtectedAuditTests(unittest.TestCase):
    def test_encryption_round_trip_and_nonce_randomness(self):
        payload = b'{"title":"Daily News","test":"za\xff"}'
        one = secure.encrypt_bytes(payload, PASSWORD)
        two = secure.encrypt_bytes(payload, PASSWORD)
        self.assertNotEqual(one["salt"], two["salt"])
        self.assertNotEqual(one["nonce"], two["nonce"])
        self.assertNotEqual(one["ciphertext"], two["ciphertext"])
        self.assertEqual(secure.decrypt_bytes(one, PASSWORD), payload)

    def test_wrong_password_cannot_decrypt(self):
        payload = secure.encrypt_bytes(b'{"private":true}', PASSWORD)
        with self.assertRaises(Exception):
            secure.decrypt_bytes(payload, "another strong secret phrase here")

    def test_sealing_deletes_local_plaintext_and_unsealing_restores_it(self):
        with tempfile.TemporaryDirectory() as temp:
            plain = Path(temp) / "audit.json"
            sealed = Path(temp) / "audit.enc.json"
            plain.write_text('{"week":"2026-W41"}', encoding="utf-8")
            secure.seal_file(plain, sealed, PASSWORD)
            self.assertFalse(plain.exists())
            ciphertext = sealed.read_text(encoding="utf-8")
            self.assertNotIn("2026-W41", ciphertext)
            self.assertEqual(json.loads(ciphertext)["cipher"], "AES-256-GCM")
            restored = secure.unseal_file(sealed, plain, PASSWORD)
            self.assertEqual(restored["week"], "2026-W41")

    def test_missing_password_must_fail_closed(self):
        with patch.dict(os.environ, {"AUDIT_PASSWORD": ""}):
            with self.assertRaises(RuntimeError):
                secure.secret()
        with patch.dict(os.environ, {"AUDIT_PASSWORD": "1234"}):
            with self.assertRaises(RuntimeError):
                secure.secret()

    def test_invalid_metadata_is_rejected(self):
        payload = secure.encrypt_bytes(b"{}", PASSWORD)
        payload["iterations"] = 1
        with self.assertRaises(ValueError):
            secure.decrypt_bytes(payload, PASSWORD)

    def test_weekly_range(self):
        days = secure.report_week_days("2026-W41")
        self.assertEqual(len(days), 7)
        self.assertEqual(days[0], "2026-10-05")
        self.assertEqual(days[-1], "2026-10-11")


if __name__ == "__main__":
    unittest.main()
