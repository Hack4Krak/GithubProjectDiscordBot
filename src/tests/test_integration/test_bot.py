# ruff: noqa: F811
import asyncio
from unittest.mock import AsyncMock, mock_open, patch

import pytest
from hikari import RESTApp
from hikari.impl import RESTClientImpl

from src.bot import run
from src.tests.test_unit.test_utils import MockShelf, forum_channel_mock, rest_client_mock  # noqa: F401
from src.utils.data_types import ProjectItemEvent
from src.utils.error import ForumChannelNotFound


class RestClientContextManagerMock:
    rest_client_mock: RESTClientImpl

    def __init__(self, rest_client_mock):
        self.rest_client_mock = rest_client_mock

    async def __aenter__(self):
        return self.rest_client_mock

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@patch.object(RESTClientImpl, "fetch_channel", new_callable=AsyncMock)
@patch.object(RESTApp, "acquire")
@patch.object(RESTApp, "start", new_callable=AsyncMock)
@patch("os.getenv")
async def test_forum_channel_not_found(
    mock_os_getenv, _mock_restapp_start, mock_restapp_acquire, mock_fetch_channel, rest_client_mock
):
    mock_os_getenv.side_effect = ["some_token", 1, 2]
    mock_restapp_acquire.return_value = RestClientContextManagerMock(rest_client_mock)
    mock_fetch_channel.return_value = None
    with pytest.raises(ForumChannelNotFound):
        update_queue = asyncio.Queue()
        await run(update_queue)


@patch("builtins.open", new_callable=mock_open, read_data="")
@patch("shelve.open")
@patch.object(RESTClientImpl, "create_forum_post", new_callable=AsyncMock)
@patch.object(RESTClientImpl, "fetch_public_archived_threads", new_callable=AsyncMock)
@patch.object(RESTClientImpl, "fetch_active_threads", new_callable=AsyncMock)
@patch.object(RESTClientImpl, "fetch_channel", new_callable=AsyncMock)
@patch.object(RESTApp, "acquire")
@patch.object(RESTApp, "start", new_callable=AsyncMock)
@patch("os.getenv")
async def test_basic_event_only_creation(
    mock_os_getenv,
    _mock_restapp_start,
    mock_restapp_acquire,
    mock_fetch_channel,
    mock_fetch_active_threads,
    mock_fetch_public_archived_threads,
    mock_create_forum_post,
    mock_shelve_open,
    _mock_open,
    rest_client_mock,
    forum_channel_mock,
):
    mock_os_getenv.side_effect = ["some_token", 1, 2, "some_path"]
    mock_restapp_acquire.return_value = RestClientContextManagerMock(rest_client_mock)
    mock_fetch_channel.return_value = forum_channel_mock
    mock_fetch_active_threads.return_value = []
    mock_fetch_public_archived_threads.return_value = []
    mock_create_forum_post.return_value = None
    mock_shelve_open.return_value = MockShelf({})
    update_queue = asyncio.Queue()
    await update_queue.put(ProjectItemEvent(name="Test Item", sender="test_sender"))
    await run(update_queue, stop_after_one_event=True)
    mock_create_forum_post.assert_called()
