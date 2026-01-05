import asyncio
import logging
from unittest.mock import ANY, AsyncMock, patch

import pytest
from hikari import RESTApp
from hikari.impl import RESTClientImpl

from src import bot
from src.tests.conftest import MockShelf, RestClientContextManagerMock
from src.utils.data_types import ProjectItemEditedBody, SimpleProjectItemEvent
from src.utils.error import ForumChannelNotFound


@patch("shelve.open")
@patch("src.bot.fetch_item_name", new_callable=AsyncMock)
@patch.object(RESTClientImpl, "create_forum_post", new_callable=AsyncMock)
async def test_create_post(
    mock_create_forum_post,
    mock_fetch_item_name,
    mock_shelve_open,
    rest_client_mock,
    shared_forum_channel_mock,
    user_text_mention,
    post_mock,
):
    mock_fetch_item_name.return_value = "audacity4"
    mock_shelf = MockShelf()
    mock_shelve_open.return_value = mock_shelf
    mock_create_forum_post.return_value = post_mock
    message = f"Nowy task stworzony audacity4 przez: {user_text_mention}.\n Link do taska: https://github.com/orgs/my-org/projects/1?pane=issue&itemId=1"
    event = SimpleProjectItemEvent(1, "audacity4", "norbiros", "created")
    await bot.create_post(event, user_text_mention, shared_forum_channel_mock, rest_client_mock, [])
    mock_create_forum_post.assert_called_with(
        shared_forum_channel_mock.forum_channel, event.node_id, message, auto_archive_duration=10080, user_mentions=[]
    )
    assert mock_shelf.get("audacity4") == "621"


@patch("src.bot.create_post", new_callable=AsyncMock)
@patch("src.bot.retrieve_discord_id")
@patch("src.bot.get_post_id_or_post", new_callable=AsyncMock)
async def test_process_no_post(
    mock_get_post_id_or_post,
    mock_retrieve_discord_id,
    mock_create_post,
    rest_client_mock,
    shared_forum_channel_mock,
    full_post_mock,
    user_text_mention,
):
    mock_get_post_id_or_post.return_value = None
    mock_retrieve_discord_id.return_value = "123456789012345678"
    mock_create_post.return_value = full_post_mock
    event = SimpleProjectItemEvent(1, "node_id", "norbiros", "created")
    await bot.process_update(
        rest_client_mock,
        1,
        1,
        shared_forum_channel_mock,
        event,
    )

    mock_create_post.assert_called_with(
        event, user_text_mention, shared_forum_channel_mock, rest_client_mock, ["123456789012345678"]
    )


@patch.object(RESTClientImpl, "fetch_channel", new_callable=AsyncMock)
@patch("src.bot.retrieve_discord_id")
@patch("src.bot.get_post_id_or_post", new_callable=AsyncMock)
async def test_process_post_id_found(
    mock_get_post_id_or_post,
    mock_retrieve_discord_id,
    mock_fetch_channel,
    rest_client_mock,
    shared_forum_channel_mock,
    full_post_mock,
    user_text_mention,
):
    mock_get_post_id_or_post.return_value = 67
    mock_retrieve_discord_id.return_value = "123456789012345678"
    mock_fetch_channel.return_value = full_post_mock
    event = SimpleProjectItemEvent(1, "audacity4", "norbiros", "created")
    await bot.process_update(
        rest_client_mock,
        1,
        1,
        shared_forum_channel_mock,
        event,
    )

    mock_fetch_channel.assert_called_with(67)


@patch("src.bot.create_post", new_callable=AsyncMock)
@patch.object(RESTClientImpl, "fetch_channel", new_callable=AsyncMock)
@patch("src.bot.retrieve_discord_id")
@patch("src.bot.get_post_id_or_post", new_callable=AsyncMock)
async def test_process_post_fetched(
    mock_get_post_id_or_post,
    mock_retrieve_discord_id,
    mock_fetch_channel,
    mock_create_post,
    rest_client_mock,
    shared_forum_channel_mock,
    full_post_mock,
    user_text_mention,
):
    mock_get_post_id_or_post.return_value = full_post_mock
    mock_retrieve_discord_id.return_value = "123456789012345678"
    event = SimpleProjectItemEvent(1, "audacity4", "norbiros", "created")
    await bot.process_update(
        rest_client_mock,
        1,
        1,
        shared_forum_channel_mock,
        event,
    )

    mock_fetch_channel.assert_not_called()
    mock_create_post.assert_not_called()


@patch.object(logging.Logger, "error")
@patch("src.bot.retrieve_discord_id")
@patch("src.bot.get_post_id_or_post", new_callable=AsyncMock)
async def test_process_post_not_guild_public_thread(
    mock_get_post_id_or_post,
    mock_retrieve_discord_id,
    mock_logger_error,
    rest_client_mock,
    shared_forum_channel_mock,
    post_mock,
    user_text_mention,
):
    mock_get_post_id_or_post.return_value = post_mock
    mock_retrieve_discord_id.return_value = "123456789012345678"
    event = SimpleProjectItemEvent(1, "audacity4", "norbiros", "created")
    await bot.process_update(
        rest_client_mock,
        1,
        1,
        shared_forum_channel_mock,
        event,
    )

    mock_logger_error.assert_called_with("Post with ID 621 is not a GuildPublicThread.")


@patch.object(SimpleProjectItemEvent, "process", new_callable=AsyncMock)
@patch.object(RESTClientImpl, "create_message", new_callable=AsyncMock)
@patch("src.bot.retrieve_discord_id")
@patch("src.bot.get_post_id_or_post", new_callable=AsyncMock)
async def test_process_post_created_message(
    mock_get_post_id_or_post,
    mock_retrieve_discord_id,
    mock_create_message,
    mock_event_process,
    rest_client_mock,
    shared_forum_channel_mock,
    full_post_mock,
    user_text_mention,
):
    mock_get_post_id_or_post.return_value = full_post_mock
    mock_retrieve_discord_id.return_value = "123456789012345678"
    event = SimpleProjectItemEvent(1, "audacity4", "norbiros", "archived")
    mock_event_process.return_value = "Test message content"
    await bot.process_update(
        rest_client_mock,
        1,
        1,
        shared_forum_channel_mock,
        event,
    )

    mock_create_message.assert_called_with(621, "Test message content", user_mentions=["123456789012345678"])


@patch("src.bot.retrieve_discord_id")
@patch.object(RESTClientImpl, "create_message", new_callable=AsyncMock)
@patch("src.bot.get_post_id_or_post", new_callable=AsyncMock)
async def test_process_message_over_2000_chars(
    mock_get_post_id_or_post,
    mock_create_message,
    mock_retrieve_discord_id,
    rest_client_mock,
    shared_forum_channel_mock,
    full_post_mock,
    user_text_mention,
):
    mock_retrieve_discord_id.return_value = "123456789012345678"
    mock_get_post_id_or_post.return_value = full_post_mock
    long_message = "A" * 4500
    event = ProjectItemEditedBody(1, "audacity4", "Norbiros", long_message)

    await bot.process_update(
        rest_client_mock,
        1,
        1,
        shared_forum_channel_mock,
        event,
    )

    assert mock_create_message.call_count == 3


@patch("src.bot.process_update", new_callable=AsyncMock)
@patch("src.bot.fetch_forum_channel", new_callable=AsyncMock)
@patch.object(RESTApp, "acquire")
@patch.object(RESTApp, "start", new_callable=AsyncMock)
@patch("os.getenv")
async def test_bot_run(
    mock_os_getenv,
    _mock_restapp_start,
    mock_restapp_acquire,
    mock_fetch_forum_channel,
    mock_process_update,
    rest_client_mock,
    forum_channel_mock,
):
    mock_os_getenv.side_effect = ["some_token", 1, 2]
    mock_restapp_acquire.return_value = RestClientContextManagerMock(rest_client_mock)
    mock_fetch_forum_channel.return_value = forum_channel_mock
    state = asyncio.Queue()
    await state.put("event")

    await bot.run(state, stop_after_one_event=True)
    mock_process_update.assert_called_with(rest_client_mock, 1, 2, ANY, "event")


@patch("src.bot.fetch_forum_channel", new_callable=AsyncMock)
@patch.object(RESTApp, "acquire")
@patch.object(RESTApp, "start", new_callable=AsyncMock)
@patch("os.getenv")
async def test_bot_run_forum_channel_is_none(
    mock_os_getenv,
    _mock_restapp_start,
    mock_restapp_acquire,
    mock_fetch_forum_channel,
    rest_client_mock,
):
    mock_os_getenv.side_effect = ["some_token", 1, 2]
    mock_restapp_acquire.return_value = RestClientContextManagerMock(rest_client_mock)
    mock_fetch_forum_channel.return_value = None
    state = asyncio.Queue()

    with pytest.raises(ForumChannelNotFound):
        await bot.run(state, stop_after_one_event=True)


@patch("src.bot.bot_logger.error")
@patch("src.bot.process_update", new_callable=AsyncMock)
@patch("src.bot.fetch_forum_channel", new_callable=AsyncMock)
@patch.object(RESTApp, "acquire")
@patch.object(RESTApp, "start", new_callable=AsyncMock)
@patch("os.getenv")
async def test_bot_run_exception_during_process(
    mock_os_getenv,
    _mock_restapp_start,
    mock_restapp_acquire,
    mock_fetch_forum_channel,
    mock_process_update,
    mock_logger_error,
    rest_client_mock,
    forum_channel_mock,
):
    mock_os_getenv.side_effect = ["some_token", 1, 2]
    mock_restapp_acquire.return_value = RestClientContextManagerMock(rest_client_mock)
    mock_fetch_forum_channel.return_value = forum_channel_mock
    mock_process_update.side_effect = Exception("Some error occurred")
    state = asyncio.Queue()
    await state.put("event")

    await bot.run(state, stop_after_one_event=True)
    for _ in range(500):  # up to ~0.5 seconds total
        try:
            mock_logger_error.assert_called_with("Error processing update: Some error occurred")
            break
        except AssertionError:
            pass
        await asyncio.sleep(0.001)
    else:
        pytest.fail("Expected log 'Error processing update: Some error occurred' not found in output")
