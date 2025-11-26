import logging
import os

import yaml
from aiorwlock import RWLock
from hikari import GuildForumChannel


class SharedForumChannel:
    forum_channel: GuildForumChannel
    lock: RWLock

    def __init__(self, forum_channel: GuildForumChannel):
        self.forum_channel = forum_channel
        self.lock = RWLock()


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


server_logger = logging.getLogger("uvicorn.error")
bot_logger = get_bot_logger()
