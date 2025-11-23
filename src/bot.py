import asyncio
import logging
import os

from hikari import GuildPublicThread, RESTApp, TokenType
from hikari.impl import RESTClientImpl

from src.utils.data_types import ProjectItemEvent
from src.utils.discord_rest_client import fetch_forum_channel, get_post_id
from src.utils.error import ForumChannelNotFound
from src.utils.misc import SharedForumChannel, add_bot_log_prefix, retrieve_discord_id


async def run(state: asyncio.Queue[ProjectItemEvent], logger: logging.Logger, stop_after_one_event: bool = False):
    discord_rest = RESTApp()
    await discord_rest.start()

    async with discord_rest.acquire(os.getenv("DISCORD_BOT_TOKEN"), token_type=TokenType.BOT) as client:
        logger.info(add_bot_log_prefix("Discord client acquired."))
        forum_channel_id = int(os.getenv("FORUM_CHANNEL_ID"))
        discord_guild_id = int(os.getenv("DISCORD_GUILD_ID"))
        forum_channel = await fetch_forum_channel(client, forum_channel_id)
        if forum_channel is None:
            raise ForumChannelNotFound(f"Forum channel with ID {forum_channel_id} not found.")
        shared_forum_channel = SharedForumChannel(forum_channel)

        while True:
            try:
                await process_update(client, forum_channel_id, discord_guild_id, shared_forum_channel, state, logger)
            except Exception as error:
                logger.error(add_bot_log_prefix(f"Error processing update: {error}"))
            if stop_after_one_event:
                break


async def process_update(
    client: RESTClientImpl,
    forum_channel_id: int,
    discord_guild_id: int,
    shared_forum_channel: SharedForumChannel,
    state: asyncio.Queue[ProjectItemEvent],
    logger: logging.Logger,
):
    event = await state.get()
    logger.info(add_bot_log_prefix(f"Processing event for item: {event.name}"))

    post_id_or_post = await get_post_id(event.name, discord_guild_id, forum_channel_id, client)
    author_discord_id = retrieve_discord_id(event.sender)
    user_mentions = [author_discord_id] if author_discord_id else []
    user_text_mention = f"<@{author_discord_id}>" if author_discord_id else "nieznany użytkownik"

    if post_id_or_post is None:
        logger.info(add_bot_log_prefix(f"Post not found, creating new post for item: {event.name}"))
        message = f"Nowy task stworzony {event.name} przez: {user_text_mention}"
        async with shared_forum_channel.lock.reader_lock:
            post: GuildPublicThread = await client.create_forum_post(
                shared_forum_channel.forum_channel,
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
            logger.error(add_bot_log_prefix(f"Post with ID {post.id} is not a GuildPublicThread."))
        except AttributeError:
            logger.error(add_bot_log_prefix(f"Post with ID {post_id_or_post} is not a GuildPublicThread."))
        return

    message = await event.process(user_text_mention, post, client, logger, shared_forum_channel, forum_channel_id)
    if message:
        await client.create_message(post.id, message, user_mentions=user_mentions)
