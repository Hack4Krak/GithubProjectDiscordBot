import asyncio
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


def create_item_link(item_id: int) -> str:
    organization_name = os.getenv("GITHUB_ORGANIZATION_NAME", "my-org")
    project_number = os.getenv("GITHUB_PROJECT_NUMBER", "1")
    return f"https://github.com/orgs/{organization_name}/projects/{project_number}?pane=issue&itemId={item_id}"


def handle_task_exception(task: asyncio.Task, error_message: str):
    try:
        exception = task.exception()
    except asyncio.CancelledError:
        return

    if exception:
        bot_logger.error(f"{error_message} {exception}")


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
