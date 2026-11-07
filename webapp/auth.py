"""Instructor-side credential, session and receipt handling."""

import hashlib
import hmac
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

LAB_ID = "AI-Backdoor-01"
CHALLENGE_ID = "trigger-v1"
SESSION_TTL = 3600
STUDENT_ID = re.compile(r"[A-Za-z0-9_-]{1,40}")
HEX_DIGEST = re.compile(r"[0-9a-f]{64}")


def credential_digest(code):
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Auth:
    key: bytes
    roster: dict[str, str]

    @classmethod
    def load(cls, path):
        config = Path(path).read_text(encoding="utf-8")
        data = json.loads(config)
        key, roster = data["key"], data["roster"]
        if not HEX_DIGEST.fullmatch(key) or not roster or not all(
            STUDENT_ID.fullmatch(student_id) and HEX_DIGEST.fullmatch(digest)
            for student_id, digest in roster.items()
        ):
            raise ValueError("Invalid lab credential configuration")
        return cls(bytes.fromhex(key), roster)

    def mac(self, message):
        return hmac.new(self.key, message.encode("ascii"), hashlib.sha256).hexdigest()

    def authenticate(self, student_id, code):
        digest = self.roster.get(student_id)
        if not hmac.compare_digest(digest or "0" * 64, credential_digest(code)) or not digest:
            return None
        expires = int(time.time()) + SESSION_TTL
        return f"{student_id}.{expires}.{self.session_signature(student_id, expires, digest)}"

    def session_signature(self, student_id, expires, digest):
        return self.mac(f"session:{LAB_ID}:{student_id}:{expires}:{digest}")

    def session_student(self, cookie):
        parts = (cookie or "").split(".")
        if len(parts) != 3:
            return None
        student_id, expires, signature = parts
        digest = self.roster.get(student_id)
        if not digest or not re.fullmatch(r"[0-9]{1,12}", expires) or not HEX_DIGEST.fullmatch(signature):
            return None
        if int(expires) <= time.time():
            return None
        if hmac.compare_digest(signature, self.session_signature(student_id, int(expires), digest)):
            return student_id
        return None

    def receipt(self, student_id):
        return self.mac(f"{LAB_ID}:{student_id}:{CHALLENGE_ID}")

    def verify_receipt(self, student_id, receipt):
        return bool(
            student_id in self.roster and HEX_DIGEST.fullmatch(receipt)
            and hmac.compare_digest(receipt, self.receipt(student_id))
        )
