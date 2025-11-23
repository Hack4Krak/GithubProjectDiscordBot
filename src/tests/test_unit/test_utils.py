import datetime
from unittest.mock import AsyncMock, mock_open, patch

import pytest
from aiohttp import ClientSession
from fastapi import HTTPException
from hikari import (
    ChannelFlag,
    ForumLayoutType,
    ForumSortOrderType,
    ForumTag,
    GuildForumChannel,
    PartialChannel,
    RESTAware,
    Snowflake,
)
from hikari.impl import EntityFactoryImpl, HTTPSettings, ProxySettings, RESTClientImpl

from src.utils import discord_rest_client, github_api
from src.utils import misc as utils


class MockShelf(dict):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class MockResponse(dict):
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def json(self):
        return self


@pytest.fixture
def rest_client_mock():
    entity_factory = EntityFactoryImpl(app=RESTAware)
    http_settings = HTTPSettings()
    proxy_settings = ProxySettings()
    return RESTClientImpl(
        cache=None,
        entity_factory=entity_factory,
        executor=None,
        http_settings=http_settings,
        proxy_settings=proxy_settings,
        token=None,
        token_type=None,
        rest_url=None,
    )


@pytest.fixture()
def post_mock():
    return PartialChannel(app=RESTAware, id=Snowflake(621), name="audacity4", type=0)


@pytest.fixture()
def forum_channel_mock():
    mock_timedelta = datetime.timedelta(seconds=0)
    return GuildForumChannel(
        app=RESTAware,
        id=Snowflake(67),
        name="forum-channel",
        topic="A forum channel",
        is_nsfw=False,
        default_auto_archive_duration=mock_timedelta,
        available_tags=[ForumTag(id=Snowflake(1), name="Size: smol", moderated=False)],
        type=0,
        guild_id=Snowflake(41),
        parent_id=None,
        position=0,
        permission_overwrites={},
        last_thread_id=None,
        rate_limit_per_user=mock_timedelta,
        default_thread_rate_limit_per_user=mock_timedelta,
        flags=ChannelFlag(0),
        default_sort_order=ForumSortOrderType.CREATION_DATE,
        default_layout=ForumLayoutType.GALLERY_VIEW,
        default_reaction_emoji_id=None,
        default_reaction_emoji_name=None,
    )


@patch("shelve.open")
async def test_get_item_name_exist_in_db(mock_shelve_open):
    mock_db = {"O_kgDOCUX8Wg": "crabcraft"}
    mock_shelve_open.return_value = MockShelf(mock_db)

    assert await utils.get_item_name("O_kgDOCUX8Wg") == "crabcraft"


@patch("shelve.open")
@patch("src.utils.misc.fetch_item_name", new_callable=AsyncMock)
async def test_get_item_name_doesnt_exist_in_db(mock_fetch_item_name, mock_shelve_open):
    mock_shelf = MockShelf({})
    mock_shelve_open.return_value = mock_shelf
    mock_fetch_item_name.return_value = "crabcraft"

    assert await utils.get_item_name("O_kgDOCUX8Wg") == "crabcraft"
    assert mock_shelf.get("O_kgDOCUX8Wg") == "crabcraft"


@patch.object(ClientSession, "post")
async def test_fetch_item_name_success(mock_post_request):
    mock_response = {"data": {"node": {"content": {"title": "42"}}}}
    mock_post_request.return_value = MockResponse(mock_response)

    assert await utils.fetch_item_name("<node_id>") == "42"


@patch.object(ClientSession, "post")
async def test_fetch_item_name_partial(mock_post_request):
    mock_response = {"data": {"node": {"content": None}}}
    mock_post_request.return_value = MockResponse(mock_response)

    with pytest.raises(HTTPException) as exception:
        await utils.fetch_item_name("<node_id>")

    assert exception.value.status_code == 500
    assert exception.value.detail == "Could not fetch item name."


@patch.object(ClientSession, "post")
async def test_fetch_item_name_none(mock_post_request):
    mock_post_request.return_value = MockResponse({})

    with pytest.raises(HTTPException) as exception:
        await utils.fetch_item_name("<node_id>")
    assert exception.value.status_code == 500
    assert exception.value.detail == "Could not fetch item name."


@patch.object(ClientSession, "post")
async def test_fetch_assignees_success(mock_post_request):
    mock_response = {
        "data": {
            "node": {
                "content": {"assignees": {"nodes": [{"id": "MDQ6VXNlcjg4MjY4MDYz"}, {"id": "MDQ6VXNlcjg5ODM3NzI0"}]}}
            }
        }
    }
    mock_post_request.return_value = MockResponse(mock_response)

    assert await github_api.fetch_assignees("<node_id>") == ["MDQ6VXNlcjg4MjY4MDYz", "MDQ6VXNlcjg5ODM3NzI0"]


@patch.object(ClientSession, "post")
async def test_fetch_assignees_partial(mock_post_request):
    mock_response = {"data": {"node": {"content": None}}}
    mock_post_request.return_value = MockResponse(mock_response)

    assert await github_api.fetch_assignees("<node_id>") == []


@patch.object(ClientSession, "post")
async def test_fetch_assignees_none(mock_post_request):
    mock_post_request.return_value = MockResponse({})

    assert await github_api.fetch_assignees("<node_id>") == []


@patch.object(ClientSession, "post")
async def test_fetch_single_select_value_success(mock_post_request):
    mock_response = {"data": {"node": {"fieldValueByName": {"name": "Dziengiel"}}}}
    mock_post_request.return_value = MockResponse(mock_response)

    assert await github_api.fetch_single_select_value("<node_id>", "Salieri") == "Dziengiel"


@patch.object(ClientSession, "post")
async def test_fetch_single_select_value_partial(mock_post_request):
    mock_response = {"data": {"node": {"fieldValueByName": None}}}
    mock_post_request.return_value = MockResponse(mock_response)

    assert await github_api.fetch_single_select_value("<node_id>", "Salieri") is None


@patch.object(ClientSession, "post")
async def test_fetch_single_select_value_none(mock_post_request):
    mock_response = {}
    mock_post_request.return_value = MockResponse(mock_response)

    assert await github_api.fetch_single_select_value("<node_id>", "Salieri") is None


@patch("shelve.open")
async def test_get_post_id_exist_in_db(mock_shelve_open, rest_client_mock):
    mock_db = {"audacity4": 621}
    mock_shelve_open.return_value = MockShelf(mock_db)

    assert await discord_rest_client.get_post_id("audacity4", 1, 1, rest_client_mock) == 621


@patch.object(RESTClientImpl, "fetch_active_threads", new_callable=AsyncMock)
@patch("shelve.open")
async def test_get_post_id_active_thread(mock_shelve_open, mock_fetch_active_threads, rest_client_mock, post_mock):
    mock_shelf = MockShelf({})
    mock_shelve_open.return_value = mock_shelf
    mock_fetch_active_threads.return_value = [post_mock]

    assert await discord_rest_client.get_post_id("audacity4", 1, 1, rest_client_mock) == post_mock
    assert mock_shelf.get("audacity4") == 621


@patch.object(RESTClientImpl, "fetch_public_archived_threads", new_callable=AsyncMock)
@patch.object(RESTClientImpl, "fetch_active_threads", new_callable=AsyncMock)
@patch("shelve.open")
async def test_get_post_id_archived_thread(
    mock_shelve_open, mock_fetch_active_threads, mock_fetch_public_archived_threads, rest_client_mock, post_mock
):
    mock_shelf = MockShelf({})
    mock_shelve_open.return_value = mock_shelf
    mock_fetch_active_threads.return_value = []
    mock_fetch_public_archived_threads.return_value = [post_mock]

    assert await discord_rest_client.get_post_id("audacity4", 1, 1, rest_client_mock) == post_mock
    assert mock_shelf.get("audacity4") == 621


@patch("builtins.open", new_callable=mock_open, read_data='MDQ6VXNlcjY2NTE0ODg1: "393756120952602625"')
@patch("yaml.load")
def test_retrieve_discord_id_present_id(mock_yaml_load, _mock_open_file):
    mock_yaml_load.return_value = {"MDQ6VXNlcjY2NTE0ODg1": "393756120952602625"}

    assert utils.retrieve_discord_id("MDQ6VXNlcjY2NTE0ODg1") == "393756120952602625"


@patch("builtins.open", new_callable=mock_open, read_data="")
def test_retrieve_discord_id_absent_id(_mock_open_file):
    assert utils.retrieve_discord_id("<node_id>") is None


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


def test_generate_signature():
    expected_signature = "sha256=9b40ac77c0653bed6e678ebd8db8b8d96a7c8ea8983b1a77577797d0a43b97c6"
    signature = utils.generate_signature("H-letter", b"I freaking love H letter")

    assert signature == expected_signature


def test_verify_secret_correct():
    secret = "H-letter"
    payload = b"I freaking love H letter"
    signature_header = "sha256=9b40ac77c0653bed6e678ebd8db8b8d96a7c8ea8983b1a77577797d0a43b97c6"

    assert utils.verify_secret(secret, payload, signature_header)


def test_verify_secret_incorrect():
    secret = "H-letter"
    payload = b"malicious"
    signature_header = "sha256=9b40ac77c0653bed6e678ebd8db8b8d96a7c8ea8983b1a77577797d0a43b97c6"

    assert not utils.verify_secret(secret, payload, signature_header)
