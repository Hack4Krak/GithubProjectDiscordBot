# ruff: noqa: F811
import asyncio
import json
from logging import Logger
from unittest.mock import AsyncMock, mock_open, patch

import aiohttp
import pytest
from hikari import RESTApp
from hikari.impl import RESTClientImpl
from uvicorn import Config, Server

from src.server import app
from src.tests.test_integration.test_bot import RestClientContextManagerMock
from src.tests.test_unit.test_bot import post_mock  # noqa: F401
from src.tests.test_unit.test_utils import MockShelf, forum_channel_mock, rest_client_mock  # noqa: F401
from src.utils import generate_signature


@patch.object(Logger, "info")
@patch.object(RESTClientImpl, "create_message", new_callable=AsyncMock)
@patch("builtins.open", new_callable=mock_open, read_data="")
@patch.object(RESTClientImpl, "fetch_active_threads", new_callable=AsyncMock)
@patch("shelve.open")
@patch("os.getenv")
@patch.object(RESTClientImpl, "fetch_channel", new_callable=AsyncMock)
@patch.object(RESTApp, "acquire")
@patch.object(RESTApp, "start", new_callable=AsyncMock)
async def test_e2e(
    _mock_restapp_start,
    mock_restapp_acquire,
    mock_fetch_channel,
    mock_getenv,
    mock_shelve_open,
    mock_fetch_active_threads,
    _mock_open,
    mock_create_message,
    mock_logger,
    rest_client_mock,
    forum_channel_mock,
    post_mock,
):
    mock_restapp_acquire.return_value = RestClientContextManagerMock(rest_client_mock)
    mock_fetch_channel.side_effect = [forum_channel_mock, post_mock]
    mock_getenv.side_effect = ["some_token", 1, 2, "some_secret", "fake_project_id", "meow.yaml"]
    post_id_shelf = MockShelf({})
    mock_shelve_open.side_effect = [MockShelf({"item123": "audacity4"}), post_id_shelf]
    mock_fetch_active_threads.return_value = [post_mock]
    config = Config(app=app, host="127.0.0.1", port=8000, log_level="critical")
    server = Server(config=config)

    server_task = asyncio.create_task(server.serve())
    for _ in range(100):
        try:
            _, writer = await asyncio.open_connection("127.0.0.1", 8000)
            writer.close()
            await writer.wait_closed()
            break
        except ConnectionRefusedError:
            await asyncio.sleep(0.01)
    else:
        pytest.fail("Server did not start in time")

    payload = {
        "action": "edited",
        "sender": {"node_id": "github_user"},
        "projects_v2_item": {"node_id": "item123", "project_node_id": "fake_project_id"},
        "changes": {"body": {"to": "Updated description"}},
    }
    signature = generate_signature("some_secret", json.dumps(payload).encode())
    async with aiohttp.ClientSession() as client:
        resp = await client.post(
            "http://127.0.0.1:8000/webhook_endpoint", json=payload, headers={"X-Hub-Signature-256": signature}
        )

    assert resp.status == 200

    for _ in range(500):  # up to ~5 seconds total
        try:
            mock_logger.assert_any_call("[BOT] Post audacity4 body updated.")
            break
        except AssertionError:
            pass
        await asyncio.sleep(0.01)
    else:
        pytest.fail("Expected log 'body updated' not found in output")
    assert post_id_shelf.get("audacity4") == 621
    mock_create_message.assert_called_with(
        621, "Opis taska zaktualizowany przez: nieznany użytkownik. Nowy opis: \nUpdated description", user_mentions=[]
    )

    server.should_exit = True
    await server_task
