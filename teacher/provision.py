"""Issue one random login code per roster entry and one classroom HMAC key."""

import argparse
import csv
import json
import os
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "webapp"))
from auth import STUDENT_ID, credential_digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roster", type=Path, help="Text file containing one student ID per line")
    parser.add_argument("--out", type=Path, default=ROOT / "private")
    args = parser.parse_args()
    ids = [line.strip() for line in args.roster.read_text(encoding="utf-8-sig").splitlines()
           if line.strip()]
    if not ids or len(ids) != len(set(ids)) or not all(STUDENT_ID.fullmatch(x) for x in ids):
        parser.error("Danh sách phải gồm MSSV duy nhất, dài 1–40 ký tự [A-Za-z0-9_-].")

    args.out.mkdir(mode=0o700, exist_ok=False)
    codes = {student_id: secrets.token_urlsafe(32) for student_id in ids}
    data = {
        "key": secrets.token_hex(32),
        "roster": {student_id: credential_digest(code) for student_id, code in codes.items()},
    }
    auth = args.out / "auth.json"
    auth.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    # Compose mounts the file itself. The host directory protects it from other users.
    auth.chmod(0o444)
    login_csv = args.out / "login-codes.csv"
    descriptor = os.open(login_csv, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["student_id", "login_code"])
        writer.writerows(codes.items())
    print(f"Issued {len(codes)} login codes in {args.out}.")


if __name__ == "__main__":
    main()
