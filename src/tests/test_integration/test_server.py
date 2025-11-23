import asyncio
import json
import logging
from typing import Any
from unittest.mock import patch

from aiohttp import ClientSession
from fastapi.testclient import TestClient

from src.server import app
from src.tests.utils import MockResponse, MockShelf
from src.utils.signature_verification import generate_signature

test_client = TestClient(app)
test_client.app.logger = logging.getLogger("uvicorn.error")
test_client.app.update_queue = asyncio.Queue()


def test_missing_body():
    response = test_client.post("/webhook_endpoint", data=None)
    assert response.status_code == 400
    assert response.json() == {"detail": "Missing request body."}


def test_github_project_node_id_mismatch():
    payload: dict[str, Any] = {
        "projects_v2_item": {"project_node_id": "wrong_id", "node_id": "123"},
        "action": "edited",
        "changes": {"field_value": {"field_type": "title", "field_name": "Title"}},
        "sender": {"node_id": "456"},
    }
    payload: str = json.dumps(payload)
    signature = generate_signature(
        "some_secret",
        payload.encode("utf-8"),
    )
    response = test_client.post(
        "/webhook_endpoint",
        content=payload,
        headers={"X-Hub-Signature-256": signature},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid project_node_id."}


@patch.object(ClientSession, "post")
@patch("shelve.open")
@patch("os.getenv")
def test_edited_action(mock_os_getenv, mock_shelve_open, mock_post_request):
    payload: dict[str, Any] = {
        "projects_v2_item": {"project_node_id": "123", "node_id": "123"},
        "action": "edited",
        "changes": {"field_value": {"field_type": "title", "field_name": "Title"}},
        "sender": {"node_id": "456"},
    }
    payload: str = json.dumps(payload)
    mock_os_getenv.side_effect = ["some_secret", "123", "some_token", "db-path.db"]
    mock_shelve_open.return_value = MockShelf({"123": "Meow"})
    mock_post_request.return_value = MockResponse({"data": {"node": {"content": {"title": "Meow"}}}})
    signature = generate_signature(
        "some_secret",
        payload.encode("utf-8"),
    )
    response = test_client.post(
        "/webhook_endpoint",
        content=payload,
        headers={"X-Hub-Signature-256": signature},
    )
    assert response.json() == {"detail": "Successfully received webhook data"}
    assert response.status_code == 200
    mock_post_request.assert_called()
