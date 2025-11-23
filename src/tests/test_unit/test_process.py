# ruff: noqa: F811
from unittest.mock import AsyncMock, mock_open, patch

from hikari import ForumTag, Snowflake
from hikari.impl import RESTClientImpl

from src.tests.utils import (  # noqa: F401
    forum_channel_mock,
    full_post_mock,
    logger_mock,
    post_mock,
    rest_client_mock,
    shared_forum_channel_mock,
    user_text_mention,
)
from src.utils.data_types import (
    ProjectItemEditedAssignees,
    ProjectItemEditedBody,
    ProjectItemEditedSingleSelect,
    ProjectItemEditedTitle,
    SimpleProjectItemEvent,
)


@patch.object(RESTClientImpl, "edit_channel")
async def test_simple_project_item_event_process_archived(
    mock_edit_channel, user_text_mention, post_mock, rest_client_mock, logger_mock, shared_forum_channel_mock
):
    event = SimpleProjectItemEvent("audacity4", "norbiros", "archived")
    assert (
        await event.process(
            user_text_mention,
            post_mock,
            rest_client_mock,
            logger_mock,
            shared_forum_channel_mock,
            shared_forum_channel_mock.forum_channel.id,
        )
        == "Task zarchiwizowany przez: <@123456789012345678>."
    )
    mock_edit_channel.assert_called_with(post_mock.id, archived=True)


@patch.object(RESTClientImpl, "edit_channel")
async def test_simple_project_item_event_process_restored(
    mock_edit_channel, user_text_mention, post_mock, rest_client_mock, logger_mock, shared_forum_channel_mock
):
    event = SimpleProjectItemEvent("audacity4", "norbiros", "restored")
    assert (
        await event.process(
            user_text_mention,
            post_mock,
            rest_client_mock,
            logger_mock,
            shared_forum_channel_mock,
            shared_forum_channel_mock.forum_channel.id,
        )
        == "Task przywrócony przez: <@123456789012345678>."
    )
    mock_edit_channel.assert_called_with(post_mock.id, archived=False)


@patch.object(RESTClientImpl, "delete_channel")
async def test_simple_project_item_event_process_deleted(
    mock_delete_channel, user_text_mention, post_mock, rest_client_mock, logger_mock, shared_forum_channel_mock
):
    event = SimpleProjectItemEvent("audacity4", "norbiros", "deleted")
    assert (
        await event.process(
            user_text_mention,
            post_mock,
            rest_client_mock,
            logger_mock,
            shared_forum_channel_mock,
            shared_forum_channel_mock.forum_channel.id,
        )
        is None
    )
    mock_delete_channel.assert_called_with(post_mock.id)


async def test_simple_project_item_event_process_created(
    user_text_mention, post_mock, rest_client_mock, logger_mock, shared_forum_channel_mock
):
    event = SimpleProjectItemEvent("audacity4", "norbiros", "created")
    assert (
        await event.process(
            user_text_mention,
            post_mock,
            rest_client_mock,
            logger_mock,
            shared_forum_channel_mock,
            shared_forum_channel_mock.forum_channel.id,
        )
        is None
    )


async def test_project_item_edited_body(
    user_text_mention, post_mock, rest_client_mock, logger_mock, shared_forum_channel_mock
):
    event = ProjectItemEditedBody("audacity4", "norbiros", "edited_body")
    assert (
        await event.process(
            user_text_mention,
            post_mock,
            rest_client_mock,
            logger_mock,
            shared_forum_channel_mock,
            shared_forum_channel_mock.forum_channel.id,
        )
        == "Opis taska zaktualizowany przez: <@123456789012345678>. Nowy opis: \nedited_body"
    )


@patch.object(RESTClientImpl, "create_message")
@patch("builtins.open", new_callable=mock_open, read_data="node_id1: 123\nnode_id2: 321\n")
async def test_project_item_edited_assignees(
    user_text_mention, post_mock, rest_client_mock, logger_mock, shared_forum_channel_mock
):
    event = ProjectItemEditedAssignees("audacity4", "norbiros", ["node_id1", "node_id2"])
    await event.process(
        user_text_mention,
        post_mock,
        rest_client_mock,
        logger_mock,
        shared_forum_channel_mock,
        shared_forum_channel_mock.forum_channel.id,
    )

    rest_client_mock.create_message.assert_called_with(
        post_mock.id,
        "Osoby przypisane do taska edytowane, aktualni przypisani: <@123>, <@321>",
        user_mentions=[123, 321],
    )


@patch.object(RESTClientImpl, "create_message")
@patch("builtins.open", new_callable=mock_open, read_data="")
async def test_project_item_edited_assignees_not_in_mapping(
    user_text_mention, post_mock, rest_client_mock, logger_mock, shared_forum_channel_mock
):
    event = ProjectItemEditedAssignees("audacity4", "norbiros", ["node_id1", "node_id2"])
    await event.process(
        user_text_mention,
        post_mock,
        rest_client_mock,
        logger_mock,
        shared_forum_channel_mock,
        shared_forum_channel_mock.forum_channel.id,
    )

    rest_client_mock.create_message.assert_called_with(
        post_mock.id, "Osoby przypisane do taska edytowane, aktualni przypisani: ", user_mentions=[]
    )


@patch.object(RESTClientImpl, "create_message")
@patch("builtins.open", new_callable=mock_open, read_data="")
async def test_project_item_edited_assignees_no_assignees(
    user_text_mention, post_mock, rest_client_mock, logger_mock, shared_forum_channel_mock
):
    event = ProjectItemEditedAssignees("audacity4", "norbiros", [])
    await event.process(
        user_text_mention,
        post_mock,
        rest_client_mock,
        logger_mock,
        shared_forum_channel_mock,
        shared_forum_channel_mock.forum_channel.id,
    )

    rest_client_mock.create_message.assert_called_with(
        post_mock.id,
        "Osoby przypisane do taska edytowane, aktualni przypisani: Brak przypisanych osób",
        user_mentions=[],
    )


@patch.object(RESTClientImpl, "edit_channel")
async def test_project_item_edited_title(
    mock_edit_channel, user_text_mention, post_mock, rest_client_mock, logger_mock, shared_forum_channel_mock
):
    event = ProjectItemEditedTitle("audacity4", "norbiros", "edited_title")
    await event.process(
        user_text_mention,
        post_mock,
        rest_client_mock,
        logger_mock,
        shared_forum_channel_mock,
        shared_forum_channel_mock.forum_channel.id,
    )
    mock_edit_channel.assert_called_with(post_mock.id, name="edited_title")


@patch.object(RESTClientImpl, "edit_channel")
async def test_project_item_edited_single_select_existing_tag(
    mock_edit_channel,
    user_text_mention,
    full_post_mock,
    rest_client_mock,
    logger_mock,
    shared_forum_channel_mock,
    forum_channel_mock,
):
    event = ProjectItemEditedSingleSelect("audacity4", "norbiros", "smol", "Size")
    await event.process(
        user_text_mention,
        full_post_mock,
        rest_client_mock,
        logger_mock,
        shared_forum_channel_mock,
        forum_channel_mock.id,
    )

    mock_edit_channel.assert_called_with(full_post_mock.id, applied_tags=[Snowflake(1)])


@patch("src.utils.data_types.get_new_tag")
@patch("src.utils.data_types.fetch_forum_channel", new_callable=AsyncMock)
@patch.object(RESTClientImpl, "edit_channel")
async def test_project_item_edited_single_select_tag_unavailable(
    mock_edit_channel,
    mock_fetch_forum_channel,
    mock_get_new_tag,
    user_text_mention,
    full_post_mock,
    rest_client_mock,
    logger_mock,
    shared_forum_channel_mock,
    forum_channel_mock,
):
    event = ProjectItemEditedSingleSelect("audacity4", "norbiros", "medium", "Size")
    new_tag = ForumTag(id=Snowflake(0), name="Size: medium")
    mock_fetch_forum_channel.return_value = forum_channel_mock
    mock_get_new_tag.side_effect = [None, new_tag]

    await event.process(
        user_text_mention,
        full_post_mock,
        rest_client_mock,
        logger_mock,
        shared_forum_channel_mock,
        forum_channel_mock.id,
    )

    mock_edit_channel.assert_any_call(
        67,
        available_tags=[*shared_forum_channel_mock.forum_channel.available_tags, new_tag],
    )
    mock_edit_channel.assert_called_with(full_post_mock.id, applied_tags=[Snowflake(0)])
