# ruff: noqa: F811 ruff recognizes fixture use as argument as redefinition
from logging import Logger
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from src.utils import signature_verification


def test_generate_signature():
    expected_signature = "sha256=9b40ac77c0653bed6e678ebd8db8b8d96a7c8ea8983b1a77577797d0a43b97c6"
    signature = signature_verification.generate_signature("H-letter", b"I freaking love H letter")

    assert signature == expected_signature


def test_verify_secret_correct():
    secret = "H-letter"
    payload = b"I freaking love H letter"
    signature_header = "sha256=9b40ac77c0653bed6e678ebd8db8b8d96a7c8ea8983b1a77577797d0a43b97c6"

    assert signature_verification.verify_secret(secret, payload, signature_header)


def test_verify_secret_incorrect():
    secret = "H-letter"
    payload = b"malicious"
    signature_header = "sha256=9b40ac77c0653bed6e678ebd8db8b8d96a7c8ea8983b1a77577797d0a43b97c6"

    assert not signature_verification.verify_secret(secret, payload, signature_header)


@patch.object(Logger, "warning")
@patch("os.getenv")
def test_verify_signature_correct(mock_getenv, mock_logger_warning):
    signature = "sha256=9b40ac77c0653bed6e678ebd8db8b8d96a7c8ea8983b1a77577797d0a43b97c6"
    body_bytes = b"I freaking love H letter"
    mock_getenv.return_value = "H-letter"

    signature_verification.verify_signature(signature, body_bytes)
    mock_logger_warning.assert_not_called()


@patch("os.getenv")
def test_verify_signature_incorrect(mock_getenv):
    signature = "sha256=9b40ac77c0653bed6e678ebd8db8b8d96a7c8ea8983b1a77577797d0a43b97c6"
    body_bytes = b"I freaking love H letter"
    mock_getenv.return_value = "K-letter"

    with pytest.raises(HTTPException) as error:
        signature_verification.verify_signature(signature, body_bytes)

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid signature."


@patch("os.getenv")
def test_verify_signature_missing(mock_getenv):
    body_bytes = b"I freaking love H letter"
    mock_getenv.return_value = "K-letter"

    with pytest.raises(HTTPException) as error:
        signature_verification.verify_signature("", body_bytes)

    assert error.value.status_code == 401
    assert error.value.detail == "Missing signature."


@patch.object(Logger, "warning")
@patch("os.getenv")
def test_verify_signature_not_set(mock_getenv, mock_logger_warning):
    signature = "sha256=9b40ac77c0653bed6e678ebd8db8b8d96a7c8ea8983b1a77577797d0a43b97c6"
    body_bytes = b"I freaking love H letter"
    mock_getenv.return_value = ""

    signature_verification.verify_signature(signature, body_bytes)
    mock_logger_warning.assert_called_with("GITHUB_WEBHOOK_SECRET is not set; skipping signature verification.")
