"""Authenticated-at-rest editorial reports for static Daily News.

The repository and Pages hosting are public. Reports are encrypted with a
strong ADMIN_AUDIT_PASSWORD secret and decrypted in the admin browser only.
The public code contains no password or derived key.
"""
import argparse
import base64
import json
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ROOT = Path(__file__).resolve().parents[1]
PLAIN_COVERAGE = ROOT / "reports" / "coverage"
ENCRYPTED_COVERAGE = ROOT / "secure" / "coverage"
PLAIN_AUDITS = ROOT / "reports" / "audits"
ENCRYPTED_AUDITS = ROOT / "secure" / "audits"
ITERATIONS = 250_000


def secret():
    value = os.environ.get("AUDIT_PASSWORD") or ""
    if len(value) < 16:
        raise RuntimeError(
            "Brak poprawnego sekretu AUDIT_PASSWORD (minimum 16 znaków). "
            "Dodaj go w repozytorium do Settings → Secrets and variables → Actions."
        )
    return value


def derive_key(password, salt, iterations=ITERATIONS):
    return PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32, salt=salt,
        iterations=iterations,
    ).derive(password.encode("utf-8"))


def encrypt_bytes(raw, password):
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = derive_key(password, salt)
    ciphertext = AESGCM(key).encrypt(nonce, raw, None)
    return {
        "version": 1,
        "cipher": "AES-256-GCM",
        "kdf": "PBKDF2-SHA256",
        "iterations": ITERATIONS,
        "salt": base64.b64encode(salt).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }


def decrypt_bytes(payload, password):
    if (payload.get("version") != 1 or
        payload.get("cipher") != "AES-256-GCM" or
        payload.get("kdf") != "PBKDF2-SHA256"):
        raise ValueError("Nieobsługiwany format zaszyfrowanego raportu.")
    iterations = int(payload["iterations"])
    if not 100_000 <= iterations <= 1_000_000:
        raise ValueError("Niepoprawna liczba iteracji PBKDF2.")
    salt = base64.b64decode(payload["salt"], validate=True)
    nonce = base64.b64decode(payload["nonce"], validate=True)
    ciphertext = base64.b64decode(payload["ciphertext"], validate=True)
    if len(salt) != 16 or len(nonce) != 12:
        raise ValueError("Niepoprawna długość parametrów szyfrowania.")
    key = derive_key(password, salt, iterations)
    return AESGCM(key).decrypt(nonce, ciphertext, None)


def seal_file(source, destination, password):
    raw = source.read_bytes()
    # Validate before sealing so no malformed report is published.
    json.loads(raw.decode("utf-8"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(encrypt_bytes(raw, password), indent=2) + "\n",
        encoding="utf-8"
    )
    source.unlink()


def unseal_file(source, destination, password):
    encrypted = json.loads(source.read_text(encoding="utf-8"))
    plaintext = decrypt_bytes(encrypted, password)
    data = json.loads(plaintext.decode("utf-8"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    return data


def report_week_days(value=None):
    if value:
        match = re.fullmatch(r"(\d{4})-W(\d{2})", value)
        if not match:
            raise ValueError("Niepoprawny tydzień. Oczekiwano YYYY-Www.")
        year, week = map(int, match.groups())
        monday = date.fromisocalendar(year, week, 1)
    else:
        local_today = datetime.now(ZoneInfo("Europe/Warsaw")).date()
        monday = local_today - timedelta(days=local_today.weekday()+7)
    return [(monday + timedelta(days=i)).isoformat() for i in range(7)]


def seal_coverage():
    password = secret()
    for path in sorted(PLAIN_COVERAGE.glob("????-??-??.json")):
        seal_file(path, ENCRYPTED_COVERAGE / (path.stem + ".enc.json"), password)
        print("Zaszyfrowano dzienny raport: " + path.stem)
    if PLAIN_COVERAGE.exists():
        if any(PLAIN_COVERAGE.glob("*.json")):
            raise RuntimeError("Pozostał niezaszyfrowany raport dzienny.")


def unseal_coverage(week):
    password = secret()
    for day in report_week_days(week):
        src = ENCRYPTED_COVERAGE / (day + ".enc.json")
        if src.exists():
            unseal_file(src, PLAIN_COVERAGE / (day + ".json"), password)


def unseal_index():
    password = secret()
    src = ENCRYPTED_AUDITS / "index.enc.json"
    if src.exists():
        unseal_file(src, PLAIN_AUDITS / "index.json", password)


def seal_audits():
    password = secret()
    for path in sorted(PLAIN_AUDITS.glob("*.json")):
        seal_file(path, ENCRYPTED_AUDITS / (path.stem + ".enc.json"), password)
        print("Zaszyfrowano raport audytu: " + path.stem)


def main():
    parser = argparse.ArgumentParser(description="Szyfrowane raporty Daily News")
    parser.add_argument("command", choices=[
        "seal-coverage", "unseal-coverage", "unseal-index", "seal-audits"
    ])
    parser.add_argument("--week", default=None)
    args = parser.parse_args()
    operations = {
        "seal-coverage": seal_coverage,
        "unseal-coverage": lambda: unseal_coverage(args.week),
        "unseal-index": unseal_index,
        "seal-audits": seal_audits,
    }
    operations[args.command]()


if __name__ == "__main__":
    main()
