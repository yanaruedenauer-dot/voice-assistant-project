from __future__ import annotations
import json
import os
from dataclasses import asdict
from typing import Optional, Type
from cryptography.fernet import Fernet

KEY_PATH = "data/secret.key"
STORE_PATH = "data/user_prefs.enc"


def _get_key() -> bytes:
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(KEY_PATH):
        with open(KEY_PATH, "wb") as f:
            f.write(Fernet.generate_key())
    return open(KEY_PATH, "rb").read()


def save_prefs_encrypted(prefs_obj) -> None:
    f = Fernet(_get_key())
    payload = json.dumps(asdict(prefs_obj)).encode("utf-8")
    token = f.encrypt(payload)
    with open(STORE_PATH, "wb") as fp:
        fp.write(token)


def load_prefs_encrypted(cls: Type) -> Optional[object]:
    if not os.path.exists(STORE_PATH):
        return None
    f = Fernet(_get_key())
    data = f.decrypt(open(STORE_PATH, "rb").read())
    return cls(**json.loads(data.decode("utf-8")))


def delete_prefs() -> bool:
    if os.path.exists(STORE_PATH):
        os.remove(STORE_PATH)
        return True
    return False
