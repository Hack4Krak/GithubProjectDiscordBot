import hashlib
import hmac
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


def generate_signature(secret: str, payload: bytes) -> str:
    hash_object = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
    return f"sha256={hash_object.hexdigest()}"


def verify_secret(secret: str, payload: bytes, signature_header: str) -> bool:
    if not secret:
        return True
    expected_signature = generate_signature(secret, payload)
    return hmac.compare_digest(expected_signature, signature_header)


def add_bot_log_prefix(text: str) -> str:
    return f"[BOT] {text}"
