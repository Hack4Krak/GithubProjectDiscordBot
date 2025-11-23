import logging
import os
import shelve

import yaml
from aiorwlock import RWLock
from hikari import GuildForumChannel

from src.utils.github_api import fetch_item_name


class SharedForumChannel:
    forum_channel: GuildForumChannel
    lock: RWLock

    def __init__(self, forum_channel: GuildForumChannel):
        self.forum_channel = forum_channel
        self.lock = RWLock()


async def get_item_name(item_node_id: str) -> str | None:
    with shelve.open(os.getenv("ITEM_NAME_TO_NODE_ID_DB_PATH", "item_name_to_node_id.db")) as db:
        try:
            item_name: str = db[item_node_id]
        except KeyError:
            item_name = await fetch_item_name(item_node_id)
            db[item_node_id] = item_name

    return item_name


def retrieve_discord_id(node_id: str) -> str | None:
    with open(os.getenv("GITHUB_ID_TO_DISCORD_ID_MAPPING_PATH", "github_id_to_discord_id_mapping.yaml")) as file:
        mapping: dict[str, str] = yaml.load("".join(file.readlines()), Loader=yaml.Loader)

        if mapping is None:
            return None

        return mapping.get(node_id, None)


class BotPrefixFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = f"[BOT] {record.msg}"
        return True


def get_bot_logger() -> logging.Logger:
    logger = logging.getLogger("uvicorn.error.bot")

    if not any(isinstance(f, BotPrefixFilter) for f in logger.filters):
        logger.addFilter(BotPrefixFilter())

    return logger
