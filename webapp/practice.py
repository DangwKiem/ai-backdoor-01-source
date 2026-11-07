"""Run SecureMail locally with a key generated per lab instance."""

import json
import os
import secrets
from pathlib import Path
from tempfile import NamedTemporaryFile

from app import create_app
from auth import PRACTICE_STUDENT_ID, credential_digest

PRACTICE_CODE = "lab-practice"


def from_env():
    state = Path(os.environ["STATE_DIRECTORY"])
    config = state / "auth.json"
    if not config.exists():
        data = {
            "key": secrets.token_hex(32),
            "roster": {PRACTICE_STUDENT_ID: credential_digest(PRACTICE_CODE)},
        }
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=state, delete=False) as stream:
            json.dump(data, stream)
        os.replace(stream.name, config)
    return create_app(config, cookie_secure=False, practice=True)
