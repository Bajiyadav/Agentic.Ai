import os
import time
from typing import Optional, Dict, Any
import jwt
import bcrypt
from cryptography.fernet import Fernet

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
IS_PRODUCTION = ENVIRONMENT in ("production", "prod")

INSECURE_DEV_SECRET = "3-wYk2BafHEbBZXTBNbByPMb03q9ui9OQMiIDyIsRZA"
INSECURE_DEV_ENCRYPTION = "c83cEflcFbyLz08GKoMrQdIRW8aRcs_hu5IJG1gEXP0="

_raw_secret = os.getenv("SECRET_KEY", "")
if not _raw_secret:
    if IS_PRODUCTION:
        raise RuntimeError("FATAL CRITICAL SECURITY ERROR: SECRET_KEY environment variable is not set in production!")
    _raw_secret = INSECURE_DEV_SECRET

_raw_enc_key = os.getenv("ENCRYPTION_KEY", "")
if not _raw_enc_key:
    if IS_PRODUCTION:
        raise RuntimeError("FATAL CRITICAL SECURITY ERROR: ENCRYPTION_KEY environment variable is not set in production!")
    _raw_enc_key = INSECURE_DEV_ENCRYPTION

if IS_PRODUCTION and (_raw_secret == INSECURE_DEV_SECRET or _raw_enc_key == INSECURE_DEV_ENCRYPTION):
    raise RuntimeError("FATAL CRITICAL SECURITY ERROR: Default development secret keys cannot be used in production!")

SECRET_KEY = _raw_secret
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours

ENCRYPTION_KEY = _raw_enc_key
_fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)

def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def create_access_token(data: Dict[str, Any], expires_delta_seconds: Optional[int] = None) -> str:
    """Creates a signed JWT access token."""
    to_encode = data.copy()
    expire_time = time.time() + (expires_delta_seconds or (ACCESS_TOKEN_EXPIRE_MINUTES * 60))
    to_encode.update({"exp": int(expire_time), "iat": int(time.time())})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a signed JWT token."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError as e:
        raise ValueError(f"Invalid token: {e}")

def encrypt_secret(plain_text: str) -> str:
    """Encrypts sensitive string (e.g. mailbox token or password) with AES-256."""
    return _fernet.encrypt(plain_text.encode("utf-8")).decode("utf-8")

def decrypt_secret(cipher_text: str) -> str:
    """Decrypts AES-256 ciphertext."""
    return _fernet.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
