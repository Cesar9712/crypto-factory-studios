from __future__ import annotations
import hashlib, secrets, time
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher()
def now() -> int: return int(time.time())
def hash_password(password: str) -> str: return ph.hash(password)
def verify_password(password: str, encoded: str) -> bool:
    try: return ph.verify(encoded, password)
    except VerifyMismatchError: return False
    except Exception: return False
def new_token() -> str: return secrets.token_urlsafe(32)
def token_hash(token: str) -> str: return hashlib.sha256(token.encode()).hexdigest()
def sha256_bytes(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
