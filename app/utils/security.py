import os
from cryptography.fernet import Fernet
from typing import Optional

# Normally this should be in an environment variable.
# Fernet keys must be 32 URL-safe base64-encoded bytes.
_DEFAULT_KEY = b"v8Gv9O7n0YmE-x1J4XwDk6Q2a3Uu6_H_X9G_b7Pj9Qk="
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", _DEFAULT_KEY)

def get_fernet():
    return Fernet(ENCRYPTION_KEY)

def encrypt_password(password: str) -> Optional[str]:
    if not password:
        return None
    f = get_fernet()
    encrypted = f.encrypt(password.encode())
    return encrypted.decode()

def decrypt_password(encrypted_password: str) -> Optional[str]:
    if not encrypted_password:
        return None
    f = get_fernet()
    try:
        decrypted = f.decrypt(encrypted_password.encode())
        return decrypted.decode()
    except Exception:
        return None
