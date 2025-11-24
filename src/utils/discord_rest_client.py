import os
import shelve

from hikari import ForumTag, GuildForumChannel, GuildThreadChannel
from hikari.impl import RESTClientImpl

from src.utils.github_api import fetch_item_name


async def fetch_forum_channel(client: RESTClientImpl, forum_channel_id: int) -> GuildForumChannel | None:
    forum_channel = await client.fetch_channel(forum_channel_id)
    if forum_channel is None or not isinstance(forum_channel, GuildForumChannel):
        return None
    return forum_channel


def get_new_tag(new_tag_name: str, available_tags: list[ForumTag]) -> ForumTag | None:
    new_tag = next((tag for tag in available_tags if tag.name == new_tag_name), None)
    return new_tag


async def get_post_id(
    node_id: str, discord_guild_id: int, forum_channel_id: int, rest_client: RESTClientImpl
) -> int | GuildThreadChannel | None:
    with shelve.open(os.getenv("POST_ID_DB_PATH", "post_id.db")) as db:
        try:
            post_id: str = db[node_id]
            return int(post_id)
        except KeyError:
            pass
        name = await fetch_item_name(node_id)
        for thread in await rest_client.fetch_active_threads(discord_guild_id):
            if thread.name == name:
                db[name] = thread.id
                return thread
        for thread in await rest_client.fetch_public_archived_threads(forum_channel_id):
            if thread.name == name:
                db[name] = thread.id
                return thread

    return None
