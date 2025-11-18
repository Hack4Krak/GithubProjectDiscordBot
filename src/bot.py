import asyncio
import os

from hikari import ForumTag, GuildForumChannel, GuildPublicThread, RESTApp, TokenType
from hikari.impl import RESTClientImpl

from src.utils import retrieve_discord_id
from src.utils.data_types import (
    ProjectItemEditedAssignees,
    ProjectItemEditedBody,
    ProjectItemEditedSingleSelect,
    ProjectItemEditedTitle,
    ProjectItemEvent,
    SimpleProjectItemEvent,
)
from src.utils.discord_rest_client import fetch_forum_channel, get_new_tag, get_post_id
from src.utils.error import ForumChannelNotFound
from src.utils.logging import bot_error, bot_info


async def run(state: asyncio.Queue[ProjectItemEvent], stop_after_one_event: bool = False):
    discord_rest = RESTApp()
    await discord_rest.start()

    async with discord_rest.acquire(os.getenv("DISCORD_BOT_TOKEN"), token_type=TokenType.BOT) as client:
        bot_info("Discord client acquired.")
        forum_channel_id = int(os.getenv("FORUM_CHANNEL_ID"))
        discord_guild_id = int(os.getenv("DISCORD_GUILD_ID"))
        forum_channel = await fetch_forum_channel(client, forum_channel_id)
        if forum_channel is None:
            raise ForumChannelNotFound(f"Forum channel with ID {forum_channel_id} not found.")

        while True:
            try:
                return_value = await process_update(client, forum_channel_id, discord_guild_id, forum_channel, state)
                if return_value is not None:
                    forum_channel = return_value
            except Exception as error:
                bot_error(f"Error processing update: {error}")
            if stop_after_one_event:
                break


async def process_update(
    client: RESTClientImpl,
    forum_channel_id: int,
    discord_guild_id: int,
    forum_channel: GuildForumChannel,
    state: asyncio.Queue[ProjectItemEvent],
) -> GuildForumChannel | None:
    event = await state.get()
    bot_info(f"Processing event for item: {event.name}")
    post_id_or_post = await get_post_id(event.name, discord_guild_id, forum_channel_id, client)
    author_discord_id = retrieve_discord_id(event.sender)
    user_mentions = [author_discord_id] if author_discord_id else []
    user_text_mention = f"<@{author_discord_id}>" if author_discord_id else "nieznany użytkownik"
    if post_id_or_post is None:
        bot_info(f"Post not found, creating new post for item: {event.name}")
        message = f"Nowy task stworzony {event.name} przez: {user_text_mention}.>"
        post: GuildPublicThread = await client.create_forum_post(
            forum_channel,
            event.name,
            message,
            auto_archive_duration=10080,
            user_mentions=user_mentions,
        )
    elif isinstance(post_id_or_post, int):
        post = await client.fetch_channel(post_id_or_post)
    else:
        post = post_id_or_post

    if not isinstance(post, GuildPublicThread):
        try:
            bot_error(f"Post with ID {post.id} is not a GuildPublicThread.")
        except AttributeError:
            bot_error(f"Post with ID {post_id_or_post} is not a Discord channel object.")
        return None

    if isinstance(event, SimpleProjectItemEvent):
        match event.event_type.value:
            case "archived":
                message = f"Task zarchiwizowany przez: {user_text_mention}."
                await client.edit_channel(post.id, archived=True)
                bot_info(f"Post {event.name} archived.")
            case "restored":
                message = f"Task przywrócony przez: {user_text_mention}."
                await client.edit_channel(post.id, archived=False)
                bot_info(f"Post {event.name} restored.")
            case "deleted":
                await client.delete_channel(post.id)
                bot_info(f"Post {event.name} deleted.")
                return None
    elif isinstance(event, ProjectItemEditedAssignees):
        assignee_mentions: list[str] = []
        assignee_discord_ids: list[int] = []
        if event.new_assignees:
            for assignee in event.new_assignees:
                discord_id = retrieve_discord_id(assignee)
                assignee_discord_ids.append(int(discord_id)) if discord_id else None
                if discord_id:
                    assignee_mentions.append(f"<@{discord_id}>")
        else:
            assignee_mentions.append("Brak przypisanych osób")

        message = f"Osoby przypisane do taska edytowane, aktualni przypisani: {', '.join(assignee_mentions)}"
        await client.create_message(post.id, message, user_mentions=assignee_discord_ids)
        bot_info(f"Post {event.name} assignees updated.")
        return None
    elif isinstance(event, ProjectItemEditedBody):
        message = f"Opis taska zaktualizowany przez: {user_text_mention}. Nowy opis: \n{event.new_body}"
        bot_info(f"Post {event.name} body updated.")
    elif isinstance(event, ProjectItemEditedTitle):
        await client.edit_channel(post.id, name=event.new_title)
        return None
    elif isinstance(event, ProjectItemEditedSingleSelect):
        available_tags = list(forum_channel.available_tags)
        current_tag_ids = list(post.applied_tag_ids)

        for tag in available_tags:
            if tag.id in current_tag_ids and tag.name.startswith(f"{event.value_type.value}: "):
                current_tag_ids.remove(tag.id)

        new_tag_name = f"{event.value_type.value}: {event.new_value}"[:48]
        new_tag = get_new_tag(new_tag_name, available_tags)

        if new_tag is None:
            bot_info(f"Tag {new_tag_name} not found, creating new tag.")
            await client.edit_channel(forum_channel.id, available_tags=[*available_tags, ForumTag(name=new_tag_name)])
            forum_channel = await fetch_forum_channel(client, forum_channel_id)
            if forum_channel is None:
                raise ForumChannelNotFound(f"Forum channel with ID {forum_channel_id} not found.")
            available_tags = list(forum_channel.available_tags)
            new_tag = get_new_tag(new_tag_name, available_tags)

        current_tag_ids.append(new_tag.id)

        await client.edit_channel(post.id, applied_tags=current_tag_ids)
        bot_info(f"Post {event.name} label updated.")
        return forum_channel
    else:
        return None

    await client.create_message(post.id, message, user_mentions=user_mentions)

    return None
