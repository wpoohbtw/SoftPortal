import hashlib
import hmac
import os
import secrets


HASH_NAME = 'sha256'
ITERATIONS = 210_000


def hash_password(password: str, salt: bytes | None = None) -> str:
    password_bytes = password.encode('utf-8')
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac(HASH_NAME, password_bytes, salt, ITERATIONS)
    return f'{HASH_NAME}${ITERATIONS}${salt.hex()}${digest.hex()}'


def verify_password(password: str, password_hash: str) -> bool:
    try:
        hash_name, iterations, salt_hex, digest_hex = password_hash.split('$', 3)
        expected = hashlib.pbkdf2_hmac(
            hash_name,
            password.encode('utf-8'),
            bytes.fromhex(salt_hex),
            int(iterations),
        ).hex()
    except (ValueError, TypeError):
        return False

    return hmac.compare_digest(expected, digest_hex)


def create_session_token() -> str:
    return secrets.token_urlsafe(48)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()
