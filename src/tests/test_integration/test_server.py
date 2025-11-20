import json
import logging
from typing import Any
from unittest.mock import patch

from aiohttp import ClientSession
from fastapi.testclient import TestClient

from src.server import app
from src.tests.test_unit.test_utils import MockResponse, MockShelf
from src.utils import generate_signature

test_client = TestClient(app)
test_client.app.logger = logging.getLogger("uvicorn.error")


def test_missing_body():
    response = test_client.post("/webhook_endpoint", data=None)
    assert response.status_code == 400
    assert response.json() == {"detail": "Missing request body."}


@patch("os.getenv")
def test_invalid_signature(mock_os_getenv):
    mock_os_getenv.return_value = "some_secret"

    response = test_client.post(
        "/webhook_endpoint", data={"mreow": "nya"}, headers={"X-Hub-Signature-256": "invalid_signature"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid signature."}


@patch("os.getenv")
def test_missing_signature(mock_os_getenv):
    mock_os_getenv.return_value = "some_secret"

    response = test_client.post(
        "/webhook_endpoint",
        data={"mreow": "nya"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing signature."}


@patch("os.getenv")
def test_invalid_json(mock_os_getenv):
    mock_os_getenv.return_value = "some_secret"
    signature = generate_signature("some_secret", b"invalid_json")
    response = test_client.post(
        "/webhook_endpoint",
        content="invalid_json",
        headers={"X-Hub-Signature-256": signature},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid JSON payload."}


@patch("os.getenv")
def test_missing_projects_v2_item(mock_os_getenv):
    mock_os_getenv.return_value = "some_secret"
    signature = generate_signature("some_secret", b'{"not_projects_v2_item": "data"}')
    response = test_client.post(
        "/webhook_endpoint",
        content='{"not_projects_v2_item": "data"}',
        headers={"X-Hub-Signature-256": signature},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Missing property in body: 'projects_v2_item'"}


@patch("os.getenv")
def test_missing_project_node_id(mock_os_getenv):
    mock_os_getenv.return_value = "some_secret"
    signature = generate_signature("some_secret", b'{"projects_v2_item": {"skibidi": true}}')
    response = test_client.post(
        "/webhook_endpoint",
        content='{"projects_v2_item": {"skibidi": true}}',
        headers={"X-Hub-Signature-256": signature},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Missing property in body: 'project_node_id'"}


@patch("os.getenv")
def test_invalid_project_node_id(mock_os_getenv):
    mock_os_getenv.side_effect = ["some_secret", 33]
    signature = generate_signature("some_secret", b'{"projects_v2_item": {"project_node_id": 123}}')
    response = test_client.post(
        "/webhook_endpoint",
        content='{"projects_v2_item": {"project_node_id": 123}}',
        headers={"X-Hub-Signature-256": signature},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid project_node_id."}


@patch("os.getenv")
def test_missing_item_node_id(mock_os_getenv):
    mock_os_getenv.side_effect = ["some_secret", 123]
    signature = generate_signature("some_secret", b'{"projects_v2_item": {"project_node_id": 123}}')
    response = test_client.post(
        "/webhook_endpoint",
        content='{"projects_v2_item": {"project_node_id": 123}}',
        headers={"X-Hub-Signature-256": signature},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Missing property in body: 'node_id'"}


@patch.object(ClientSession, "post")
@patch("shelve.open")
@patch("os.getenv")
def test_could_not_fetch_item_name(mock_os_getenv, mock_shelve_open, mock_post_request):
    mock_os_getenv.side_effect = ["some_secret", 123, "some_token", "db-path.db"]
    mock_shelve_open.return_value = MockShelf({})
    mock_post_request.return_value = MockResponse({})
    signature = generate_signature("some_secret", b'{"projects_v2_item": {"project_node_id": 123, "node_id": "123"}}')
    response = test_client.post(
        "/webhook_endpoint",
        content='{"projects_v2_item": {"project_node_id": 123, "node_id": "123"}}',
        headers={"X-Hub-Signature-256": signature},
    )
    assert response.status_code == 500
    assert response.json() == {"detail": "Could not fetch item name."}


@patch("shelve.open")
@patch("os.getenv")
def test_missing_action(mock_os_getenv, mock_shelve_open):
    mock_os_getenv.side_effect = ["some_secret", 123, "db-path.db"]
    mock_shelve_open.return_value = MockShelf({"123": "Meow"})
    signature = generate_signature("some_secret", b'{"projects_v2_item": {"project_node_id": 123, "node_id": "123"}}')
    response = test_client.post(
        "/webhook_endpoint",
        content='{"projects_v2_item": {"project_node_id": 123, "node_id": "123"}}',
        headers={"X-Hub-Signature-256": signature},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Missing action in payload."}


@patch.object(ClientSession, "post")
@patch("shelve.open")
@patch("os.getenv")
def test_edited_action(mock_os_getenv, mock_shelve_open, mock_post_request):
    payload: dict[str, Any] = {
        "projects_v2_item": {"project_node_id": 123, "node_id": "123"},
        "action": "edited",
        "changes": {"field_value": {"field_type": "title"}},
    }
    payload: str = json.dumps(payload)
    mock_os_getenv.side_effect = ["some_secret", 123, "some_token", "db-path.db"]
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
