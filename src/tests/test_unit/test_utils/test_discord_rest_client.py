# ruff: noqa: F811 ruff recognizes fixture use as argument as redefinition
from unittest.mock import AsyncMock, patch

from hikari import ForumTag, Snowflake
from hikari.impl import RESTClientImpl

from src.tests.utils import (  # noqa: F401 ruff recognizes fixture import as unused
    MockShelf,
    forum_channel_mock,
    post_mock,
    rest_client_mock,
)
from src.utils import discord_rest_client


@patch.object(RESTClientImpl, "fetch_channel", new_callable=AsyncMock)
async def test_fetch_forum_channel_success(mock_fetch_channel, rest_client_mock, forum_channel_mock):
    mock_fetch_channel.return_value = forum_channel_mock

    assert await discord_rest_client.fetch_forum_channel(rest_client_mock, 67) == forum_channel_mock


@patch.object(RESTClientImpl, "fetch_channel", new_callable=AsyncMock)
async def test_fetch_forum_channel_none(mock_fetch_channel, rest_client_mock):
    mock_fetch_channel.return_value = None

    assert await discord_rest_client.fetch_forum_channel(rest_client_mock, 67) is None


@patch.object(RESTClientImpl, "fetch_channel", new_callable=AsyncMock)
async def test_fetch_forum_channel_not_forum_channel(mock_fetch_channel, rest_client_mock, post_mock):
    mock_fetch_channel.return_value = post_mock

    assert await discord_rest_client.fetch_forum_channel(rest_client_mock, 67) is None


def test_get_new_tag_success():
    tag1 = ForumTag(id=Snowflake(1), name="enchantment", moderated=False)
    available_tags = [tag1]

    assert discord_rest_client.get_new_tag("enchantment", available_tags) == tag1


def test_get_new_tag_none():
    tag1 = ForumTag(id=Snowflake(1), name="enchantment", moderated=False)
    available_tags = [tag1]

    assert discord_rest_client.get_new_tag("build", available_tags) is None


@patch("shelve.open")
async def test_get_post_id_exist_in_db(mock_shelve_open, rest_client_mock):
    mock_db = {"node_id": 621}
    mock_shelve_open.return_value = MockShelf(mock_db)

    assert await discord_rest_client.get_post_id("node_id", 1, 1, rest_client_mock) == 621


@patch("src.utils.discord_rest_client.fetch_item_name", new_callable=AsyncMock)
@patch.object(RESTClientImpl, "fetch_active_threads", new_callable=AsyncMock)
@patch("shelve.open")
async def test_get_post_id_active_thread(
    mock_shelve_open, mock_fetch_active_threads, mock_fetch_item_name, rest_client_mock, post_mock
):
    mock_shelf = MockShelf({})
    mock_shelve_open.return_value = mock_shelf
    mock_fetch_active_threads.return_value = [post_mock]
    mock_fetch_item_name.return_value = "audacity4"

    assert await discord_rest_client.get_post_id("node_id", 1, 1, rest_client_mock) == post_mock
    assert mock_shelf.get("audacity4") == 621


@patch("src.utils.discord_rest_client.fetch_item_name", new_callable=AsyncMock)
@patch.object(RESTClientImpl, "fetch_public_archived_threads", new_callable=AsyncMock)
@patch.object(RESTClientImpl, "fetch_active_threads", new_callable=AsyncMock)
@patch("shelve.open")
async def test_get_post_id_archived_thread(
    mock_shelve_open,
    mock_fetch_active_threads,
    mock_fetch_public_archived_threads,
    mock_fetch_item_name,
    rest_client_mock,
    post_mock,
):
    mock_shelf = MockShelf({})
    mock_shelve_open.return_value = mock_shelf
    mock_fetch_active_threads.return_value = []
    mock_fetch_public_archived_threads.return_value = [post_mock]
    mock_fetch_item_name.return_value = "audacity4"

    assert await discord_rest_client.get_post_id("node_id", 1, 1, rest_client_mock) == post_mock
    assert mock_shelf.get("audacity4") == 621


@patch("src.utils.discord_rest_client.fetch_item_name", new_callable=AsyncMock)
@patch.object(RESTClientImpl, "fetch_public_archived_threads", new_callable=AsyncMock)
@patch.object(RESTClientImpl, "fetch_active_threads", new_callable=AsyncMock)
@patch("shelve.open")
async def test_get_post_id_none(
    mock_shelve_open,
    mock_fetch_active_threads,
    mock_fetch_public_archived_threads,
    mock_fetch_item_name,
    rest_client_mock,
    post_mock,
):
    mock_shelf = MockShelf({})
    mock_shelve_open.return_value = mock_shelf
    mock_fetch_active_threads.return_value = []
    mock_fetch_public_archived_threads.return_value = []
    mock_fetch_item_name.return_value = "audacity4"

    assert await discord_rest_client.get_post_id("node_id", 1, 1, rest_client_mock) is None
    assert mock_shelf.get("audacity4") is None
