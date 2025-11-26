import hashlib
import hmac
import os

from fastapi import HTTPException

from src.utils.misc import server_logger


def verify_signature(signature: str | None, body_bytes: bytes) -> None:
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    if not secret:
        server_logger.warning("GITHUB_WEBHOOK_SECRET is not set; skipping signature verification.")
        return
    if signature:
        correct_signature = verify_secret(secret, body_bytes, signature)
        if not correct_signature:
            raise HTTPException(status_code=401, detail="Invalid signature.")
    else:
        raise HTTPException(status_code=401, detail="Missing signature.")


def generate_signature(secret: str, payload: bytes) -> str:
    hash_object = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
    return f"sha256={hash_object.hexdigest()}"


def verify_secret(secret: str, payload: bytes, signature_header: str) -> bool:
    if not secret:
        return True
    expected_signature = generate_signature(secret, payload)
    return hmac.compare_digest(expected_signature, signature_header)
