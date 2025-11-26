import asyncio
import os

from hikari import GuildPublicThread, RESTApp, TokenType
from hikari.impl import RESTClientImpl

from src.utils.data_types import ProjectItemEvent
from src.utils.discord_rest_client import fetch_forum_channel, get_post_id
from src.utils.error import ForumChannelNotFound
from src.utils.github_api import fetch_item_name
from src.utils.misc import SharedForumChannel, bot_logger, retrieve_discord_id


async def run(state: asyncio.Queue[ProjectItemEvent], stop_after_one_event: bool = False):
    discord_rest = RESTApp()
    await discord_rest.start()

    async with discord_rest.acquire(os.getenv("DISCORD_BOT_TOKEN"), token_type=TokenType.BOT) as client:
        bot_logger.info("Discord client acquired.")
        forum_channel_id = int(os.getenv("FORUM_CHANNEL_ID"))
        discord_guild_id = int(os.getenv("DISCORD_GUILD_ID"))
        forum_channel = await fetch_forum_channel(client, forum_channel_id)
        if forum_channel is None:
            raise ForumChannelNotFound(f"Forum channel with ID {forum_channel_id} not found.")
        shared_forum_channel = SharedForumChannel(forum_channel)

        while True:
            try:
                await process_update(client, forum_channel_id, discord_guild_id, shared_forum_channel, state)
            except Exception as error:
                bot_logger.error(f"Error processing update: {error}")
            if stop_after_one_event:
                break


async def process_update(
    client: RESTClientImpl,
    forum_channel_id: int,
    discord_guild_id: int,
    shared_forum_channel: SharedForumChannel,
    state: asyncio.Queue[ProjectItemEvent],
):
    event = await state.get()
    bot_logger.info(f"Processing event for item: {event.node_id}")

    post_id_or_post = await get_post_id(event.node_id, discord_guild_id, forum_channel_id, client)
    author_discord_id = retrieve_discord_id(event.sender)
    user_mentions = [author_discord_id] if author_discord_id else []
    user_text_mention = f"<@{author_discord_id}>" if author_discord_id else "nieznany użytkownik"

    if post_id_or_post is None:
        post = await create_post(event, user_text_mention, shared_forum_channel, client, user_mentions)
    elif isinstance(post_id_or_post, int):
        post = await client.fetch_channel(post_id_or_post)
    else:
        post = post_id_or_post

    if not isinstance(post, GuildPublicThread):
        try:
            bot_logger.error(f"Post with ID {post.id} is not a GuildPublicThread.")
        except AttributeError:
            bot_logger.error(f"Post with node_id {event.node_id} is not a GuildPublicThread.")
        return

    message = await event.process(user_text_mention, post, client, shared_forum_channel, forum_channel_id)
    if message:
        await client.create_message(post.id, message, user_mentions=user_mentions)


async def create_post(
    event: ProjectItemEvent,
    user_text_mention: str,
    shared_forum_channel: SharedForumChannel,
    client: RESTClientImpl,
    user_mentions: list[str],
) -> GuildPublicThread:
    bot_logger.info(f"Post not found, creating new post for item: {event.node_id}")
    item_name = await fetch_item_name(event.node_id)
    message = f"Nowy task stworzony {item_name} przez: {user_text_mention}"
    async with shared_forum_channel.lock.reader_lock:
        return await client.create_forum_post(
            shared_forum_channel.forum_channel,
            item_name,
            message,
            auto_archive_duration=10080,
            user_mentions=user_mentions,
        )
