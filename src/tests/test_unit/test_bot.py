# ruff: noqa: F811

import asyncio
import datetime
import logging
from unittest.mock import AsyncMock, mock_open, patch

import pytest
from hikari import ChannelFlag, ForumTag, GuildPublicThread, RESTAware, Snowflake, ThreadMetadata
from hikari.impl import RESTClientImpl

from src.bot import process_update
from src.utils import SharedForumChannel
from src.utils.data_types import (
    ProjectItemEditedAssignees,
    ProjectItemEditedBody,
    ProjectItemEditedSingleSelect,
    ProjectItemEditedTitle,
    SimpleProjectItemEvent,
)

from .test_utils import forum_channel_mock, rest_client_mock  # noqa: F401


@pytest.fixture
def shared_forum_channel_mock(forum_channel_mock):
    return SharedForumChannel(forum_channel_mock)


@pytest.fixture
def post_mock():
    mock_timedelta = datetime.timedelta(seconds=0)
    mock_datetime = datetime.datetime.now()
    mock_metadata = ThreadMetadata(
        is_archived=False,
        archive_timestamp=mock_datetime,
        auto_archive_duration=mock_timedelta,
        is_invitable=False,
        is_locked=False,
        created_at=mock_datetime,
    )
    return GuildPublicThread(
        app=RESTAware,
        id=Snowflake(621),
        name="audacity4",
        type=0,
        guild_id=Snowflake(0),
        last_message_id=None,
        last_pin_timestamp=None,
        rate_limit_per_user=mock_timedelta,
        approximate_message_count=0,
        approximate_member_count=0,
        member=None,
        owner_id=Snowflake(0),
        parent_id=Snowflake(0),
        metadata=mock_metadata,
        applied_tag_ids=[Snowflake(1)],
        flags=ChannelFlag(0),
    )


@pytest.fixture
def logger_mock():
    return logging.getLogger("uvicorn.error")


@patch.object(RESTClientImpl, "create_forum_post", new_callable=AsyncMock)
@patch("src.bot.retrieve_discord_id")
@patch("src.bot.get_post_id", new_callable=AsyncMock)
async def test_process_update_created_success(
    mock_get_post_id,
    mock_retrieve_discord_id,
    mock_create_forum_post,
    shared_forum_channel_mock,
    rest_client_mock,
    logger_mock,
):
    state = asyncio.Queue()
    await state.put(SimpleProjectItemEvent("mmmocking", "norbiros", "created"))
    mock_get_post_id.return_value = None
    mock_retrieve_discord_id.return_value = 2137696742041

    await process_update(rest_client_mock, 1, 1, shared_forum_channel_mock, state, logger_mock)
    assert mock_create_forum_post.called


@patch.object(RESTClientImpl, "fetch_channel", new_callable=AsyncMock)
@patch("src.bot.retrieve_discord_id")
@patch("src.bot.get_post_id", new_callable=AsyncMock)
async def test_process_update_already_exists(
    mock_get_post_id,
    mock_retrieve_discord_id,
    mock_fetch_channel,
    shared_forum_channel_mock,
    rest_client_mock,
    logger_mock,
):
    state = asyncio.Queue()
    await state.put(SimpleProjectItemEvent("mmmocking", "norbiros", "created"))
    mock_get_post_id.return_value = 1
    mock_retrieve_discord_id.return_value = "2137696742041"

    await process_update(rest_client_mock, 1, 1, shared_forum_channel_mock, state, logger_mock)
    assert mock_fetch_channel.called


@patch.object(RESTClientImpl, "edit_channel", new_callable=AsyncMock)
@patch.object(RESTClientImpl, "create_message", new_callable=AsyncMock)
@patch.object(RESTClientImpl, "fetch_channel", new_callable=AsyncMock)
@patch("src.bot.retrieve_discord_id")
@patch("src.bot.get_post_id", new_callable=AsyncMock)
async def test_process_update_archived(
    mock_get_post_id,
    mock_retrieve_discord_id,
    mock_fetch_channel,
    mock_create_message,
    mock_edit_channel,
    shared_forum_channel_mock,
    rest_client_mock,
    post_mock,
    logger_mock,
):
    state = asyncio.Queue()
    await state.put(SimpleProjectItemEvent("audacity4", "norbiros", "archived"))
    mock_get_post_id.return_value = 621
    user_id = 2137696742041
    mock_retrieve_discord_id.return_value = user_id
    mock_fetch_channel.return_value = post_mock

    await process_update(rest_client_mock, 1, 1, shared_forum_channel_mock, state, logger_mock)
    mock_create_message.assert_called_with(
        post_mock.id, f"Task zarchiwizowany przez: <@{user_id}>.", user_mentions=[user_id]
    )
    mock_edit_channel.assert_called_with(post_mock.id, archived=True)


@patch.object(RESTClientImpl, "edit_channel", new_callable=AsyncMock)
@patch.object(RESTClientImpl, "create_message", new_callable=AsyncMock)
@patch.object(RESTClientImpl, "fetch_channel", new_callable=AsyncMock)
@patch("src.bot.retrieve_discord_id")
@patch("src.bot.get_post_id", new_callable=AsyncMock)
async def test_process_update_restored(
    mock_get_post_id,
    mock_retrieve_discord_id,
    mock_fetch_channel,
    mock_create_message,
    mock_edit_channel,
    shared_forum_channel_mock,
    rest_client_mock,
    post_mock,
    logger_mock,
):
    state = asyncio.Queue()
    await state.put(SimpleProjectItemEvent("audacity4", "norbiros", "restored"))
    mock_get_post_id.return_value = 621
    user_id = 2137696742041
    mock_retrieve_discord_id.return_value = user_id
    mock_fetch_channel.return_value = post_mock

    await process_update(rest_client_mock, 1, 1, shared_forum_channel_mock, state, logger_mock)
    mock_create_message.assert_called_with(
        post_mock.id, f"Task przywrócony przez: <@{user_id}>.", user_mentions=[user_id]
    )
    mock_edit_channel.assert_called_with(post_mock.id, archived=False)


@patch.object(RESTClientImpl, "delete_channel", new_callable=AsyncMock)
@patch.object(RESTClientImpl, "fetch_channel", new_callable=AsyncMock)
@patch("src.bot.retrieve_discord_id")
@patch("src.bot.get_post_id", new_callable=AsyncMock)
async def test_process_update_deleted(
    mock_get_post_id,
    mock_retrieve_discord_id,
    mock_fetch_channel,
    mock_delete_channel,
    shared_forum_channel_mock,
    rest_client_mock,
    post_mock,
    logger_mock,
):
    state = asyncio.Queue()
    await state.put(SimpleProjectItemEvent("audacity4", "norbiros", "deleted"))
    mock_get_post_id.return_value = 621
    mock_retrieve_discord_id.return_value = "niepodam@norbiros.dev"
    mock_fetch_channel.return_value = post_mock

    await process_update(rest_client_mock, 1, 1, shared_forum_channel_mock, state, logger_mock)
    mock_delete_channel.assert_called_with(post_mock.id)


@patch("builtins.open", new_callable=mock_open, read_data="norbiros: 2137696742041")
@patch.object(RESTClientImpl, "create_message", new_callable=AsyncMock)
@patch.object(RESTClientImpl, "fetch_channel", new_callable=AsyncMock)
@patch("src.bot.retrieve_discord_id")
@patch("src.bot.get_post_id", new_callable=AsyncMock)
async def test_process_update_assignees(
    mock_get_post_id,
    mock_retrieve_discord_id,
    mock_fetch_channel,
    mock_create_message,
    _mock_open,
    shared_forum_channel_mock,
    rest_client_mock,
    post_mock,
    logger_mock,
):
    state = asyncio.Queue()
    await state.put(ProjectItemEditedAssignees("audacity4", "norbiros", ["norbiros"]))
    mock_get_post_id.return_value = 621
    user_id = 2137696742041
    mock_retrieve_discord_id.return_value = user_id
    mock_fetch_channel.return_value = post_mock
    message = f"Osoby przypisane do taska edytowane, aktualni przypisani: <@{user_id}>"

    await process_update(rest_client_mock, 1, 1, shared_forum_channel_mock, state, logger_mock)
    mock_create_message.assert_called_with(post_mock.id, message, user_mentions=[user_id])


@patch.object(RESTClientImpl, "create_message", new_callable=AsyncMock)
@patch.object(RESTClientImpl, "fetch_channel", new_callable=AsyncMock)
@patch("src.bot.retrieve_discord_id")
@patch("src.bot.get_post_id", new_callable=AsyncMock)
async def test_process_update_body(
    mock_get_post_id,
    mock_retrieve_discord_id,
    mock_fetch_channel,
    mock_create_message,
    shared_forum_channel_mock,
    rest_client_mock,
    post_mock,
    logger_mock,
):
    state = asyncio.Queue()
    new_body = "Nowy opis taska"
    await state.put(ProjectItemEditedBody("audacity4", "norbiros", new_body))
    mock_get_post_id.return_value = 621
    user_id = 2137696742041
    mock_retrieve_discord_id.return_value = user_id
    mock_fetch_channel.return_value = post_mock
    message = f"Opis taska zaktualizowany przez: <@{user_id}>. Nowy opis: \n{new_body}"

    await process_update(rest_client_mock, 1, 1, shared_forum_channel_mock, state, logger_mock)
    mock_create_message.assert_called_with(post_mock.id, message, user_mentions=[user_id])


@patch.object(RESTClientImpl, "edit_channel", new_callable=AsyncMock)
@patch.object(RESTClientImpl, "fetch_channel", new_callable=AsyncMock)
@patch("src.bot.retrieve_discord_id")
@patch("src.bot.get_post_id", new_callable=AsyncMock)
async def test_process_update_title(
    mock_get_post_id,
    mock_retrieve_discord_id,
    mock_fetch_channel,
    mock_edit_channel,
    shared_forum_channel_mock,
    rest_client_mock,
    post_mock,
    logger_mock,
):
    state = asyncio.Queue()
    new_title = "Nowy opis taska"
    await state.put(ProjectItemEditedTitle("audacity4", "norbiros", new_title))
    mock_get_post_id.return_value = 621
    user_id = 2137696742041
    mock_retrieve_discord_id.return_value = user_id
    mock_fetch_channel.return_value = post_mock

    await process_update(rest_client_mock, 1, 1, shared_forum_channel_mock, state, logger_mock)
    mock_edit_channel.assert_called_with(post_mock.id, name=new_title)


@patch("builtins.open", new_callable=mock_open, read_data="")
@patch("src.utils.data_types.get_new_tag")
@patch.object(RESTClientImpl, "edit_channel", new_callable=AsyncMock)
@patch.object(RESTClientImpl, "fetch_channel", new_callable=AsyncMock)
@patch("src.utils.data_types.retrieve_discord_id")
@patch("src.bot.get_post_id", new_callable=AsyncMock)
async def test_process_update_single_select(
    mock_get_post_id,
    mock_retrieve_discord_id,
    mock_fetch_channel,
    mock_edit_channel,
    mock_get_new_tag,
    _mock_open,
    shared_forum_channel_mock,
    rest_client_mock,
    post_mock,
    logger_mock,
):
    state = asyncio.Queue()
    await state.put(ProjectItemEditedSingleSelect("audacity4", "norbiros", "big", "Size"))
    mock_get_post_id.return_value = 621
    user_id = 2137696742041
    mock_retrieve_discord_id.return_value = user_id
    mock_fetch_channel.return_value = post_mock
    mock_get_new_tag.return_value = ForumTag(id=Snowflake(2), name="Size: big", moderated=False)

    await process_update(rest_client_mock, 1, 1, shared_forum_channel_mock, state, logger_mock)
    mock_edit_channel.assert_called_with(post_mock.id, applied_tags=[Snowflake(2)])


@patch("src.utils.data_types.fetch_forum_channel", new_callable=AsyncMock)
@patch("src.utils.data_types.get_new_tag")
@patch.object(RESTClientImpl, "edit_channel", new_callable=AsyncMock)
@patch.object(RESTClientImpl, "fetch_channel", new_callable=AsyncMock)
@patch("src.bot.retrieve_discord_id")
@patch("src.bot.get_post_id", new_callable=AsyncMock)
async def test_process_update_single_select_tag_unavailable(
    mock_get_post_id,
    mock_retrieve_discord_id,
    mock_fetch_channel,
    mock_edit_channel,
    mock_get_new_tag,
    mock_fetch_forum_channel,
    shared_forum_channel_mock,
    forum_channel_mock,
    rest_client_mock,
    post_mock,
    logger_mock,
):
    state = asyncio.Queue()
    await state.put(ProjectItemEditedSingleSelect("audacity4", "norbiros", "big", "Size"))
    mock_get_post_id.return_value = 621
    user_id = 2137696742041
    mock_retrieve_discord_id.return_value = user_id
    mock_fetch_channel.return_value = post_mock
    mock_fetch_forum_channel.return_value = forum_channel_mock
    new_tag = ForumTag(id=Snowflake(0), name="Size: big")
    mock_get_new_tag.side_effect = [None, new_tag]

    await process_update(rest_client_mock, 1, 1, shared_forum_channel_mock, state, logger_mock)
    mock_edit_channel.assert_any_call(
        1,
        available_tags=shared_forum_channel_mock.forum_channel.available_tags + [new_tag],
    )
    mock_edit_channel.assert_called_with(post_mock.id, applied_tags=[Snowflake(0)])
