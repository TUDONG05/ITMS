from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from collections.abc import Mapping
from typing import Any


class InvalidAccessTokenError(ValueError):
    """Raised when an access token cannot be trusted."""


def hash_password(password: str) -> str:
    """Hash a password with a salted, memory-hard scrypt derivation."""
    salt = secrets.token_bytes(16)
    derived_key = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${_encode(salt)}${_encode(derived_key)}"


def verify_password(password: str, encoded_password: str) -> bool:
    """Compare a candidate password without exposing timing differences."""
    try:
        algorithm, encoded_salt, encoded_hash = encoded_password.split("$")
        if algorithm != "scrypt":
            return False
        salt = _decode(encoded_salt)
        expected_hash = _decode(encoded_hash)
        candidate_hash = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate_hash, expected_hash)


def create_access_token(
    *,
    subject: str,
    session_id: str,
    secret: str,
    issuer: str,
    audience: str,
    expires_in_seconds: int,
) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": subject,
        "sid": session_id,
        "iat": now,
        "exp": now + expires_in_seconds,
        "iss": issuer,
        "aud": audience,
    }
    header_segment = _encode_json(header)
    payload_segment = _encode_json(payload)
    signed_content = f"{header_segment}.{payload_segment}".encode()
    signature = hmac.new(secret.encode(), signed_content, hashlib.sha256).digest()
    return f"{header_segment}.{payload_segment}.{_encode(signature)}"


def decode_access_token(
    token: str,
    *,
    secret: str,
    issuer: str,
    audience: str,
) -> dict[str, Any]:
    """Validate the signature and mandatory claims of an HS256 JWT."""
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
        header = _decode_json(header_segment)
        payload = _decode_json(payload_segment)
        signed_content = f"{header_segment}.{payload_segment}".encode()
        expected_signature = hmac.new(secret.encode(), signed_content, hashlib.sha256).digest()
        actual_signature = _decode(signature_segment)
    except (AttributeError, ValueError, json.JSONDecodeError) as error:
        raise InvalidAccessTokenError from error

    if header != {"alg": "HS256", "typ": "JWT"}:
        raise InvalidAccessTokenError
    if not hmac.compare_digest(actual_signature, expected_signature):
        raise InvalidAccessTokenError
    if payload.get("iss") != issuer or payload.get("aud") != audience:
        raise InvalidAccessTokenError
    if not isinstance(payload.get("sub"), str) or not isinstance(payload.get("sid"), str):
        raise InvalidAccessTokenError
    if not isinstance(payload.get("exp"), int) or payload["exp"] <= int(time.time()):
        raise InvalidAccessTokenError
    return payload


def _encode_json(value: Mapping[str, Any]) -> str:
    return _encode(json.dumps(value, separators=(",", ":"), sort_keys=True).encode())


def _decode_json(value: str) -> dict[str, Any]:
    decoded = json.loads(_decode(value))
    if not isinstance(decoded, dict):
        raise ValueError("JWT section must be an object.")
    return decoded


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(f"{value}{'=' * (-len(value) % 4)}")
