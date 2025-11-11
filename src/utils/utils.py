import hashlib
import hmac
import os
import shelve

import aiohttp
import yaml
from hikari import ForumTag, GuildForumChannel
from hikari.impl import RESTClientImpl


async def get_item_name(item_node_id: str) -> str | None:
    with shelve.open("item_name_to_node_id.db") as db:
        try:
            item_name: str = db[item_node_id]
        except KeyError:
            item_name = await fetch_item_name(item_node_id)
            if item_name is None:
                return None
            db[item_node_id] = item_name

    return item_name


async def fetch_item_name(item_node_id: str | None) -> str | None:
    if item_node_id is None:
        return None

    query = """
    query ($id: ID!) {
      node(id: $id) {
        ... on ProjectV2Item {
          content {
            ... on DraftIssue {
              title
            }
            ... on Issue {
              title
            }
            ... on PullRequest {
              title
            }
          }
        }
      }
    }
    """

    variables = {"id": item_node_id}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": variables},
            headers={"Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}"},
        ) as response:
            response_body = await response.json()

    try:
        item_name: str | None = response_body["data"]["node"]["content"]["title"]
    except (KeyError, AttributeError):
        return None

    return item_name


async def fetch_assignees(item_node_id: str | None) -> list[str]:
    if item_node_id is None:
        return []

    query = """
    query ($id: ID!) {
      node(id: $id) {
        ... on ProjectV2Item {
          content {
            ... on DraftIssue {
              assignees(first: 10) {
                nodes {
                  id
                }
              }
            }
            ... on Issue {
              assignees(first: 10) {
                nodes {
                  id
                }
              }
            }
            ... on PullRequest {
              assignees(first: 10) {
                nodes {
                  id
                }
              }
            }
          }
        }
      }
    }
    """

    variables = {"id": item_node_id}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": variables},
            headers={"Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}"},
        ) as response:
            response_body = await response.json()
    try:
        assignees_data = response_body["data"]["node"]["content"]["assignees"]["nodes"]
    except (KeyError, AttributeError):
        return []
    assignees = [assignee.get("id", None) for assignee in assignees_data]

    return assignees


async def fetch_single_select_value(item_node_id: str | None, field_name: str | None) -> str | None:
    if item_node_id is None or field_name is None:
        return None

    query = """
    query ($id: ID!, $field_type: String!) {
      node(id: $id) {
        ... on ProjectV2Item {
          fieldValueByName(name: $field_type) {
            ... on ProjectV2ItemFieldSingleSelectValue {
              name
            }
          }
        }
      }
    }
    """

    variables = {"id": item_node_id, "field_type": field_name}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": variables},
            headers={"Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}"},
        ) as response:
            response_body = await response.json()

    try:
        name: str | None = response_body["data"]["node"]["fieldValueByName"]["name"]
    except (KeyError, AttributeError):
        return None

    return name


async def get_post_id(
    name: str, discord_guild_id: int, forum_channel_id: int, rest_client: RESTClientImpl
) -> int | None:
    with shelve.open("post_id.db") as db:
        try:
            post_id: str = db[name]
            return int(post_id)
        except KeyError:
            pass
        # todo: return post if found in active threads or in archived threads
        for thread in await rest_client.fetch_active_threads(discord_guild_id):
            if thread.name == name:
                db[name] = thread.id
                return thread.id
        for thread in await rest_client.fetch_public_archived_threads(forum_channel_id):
            if thread.name == name:
                db[name] = thread.id
                return thread.id

    return None


def retrieve_discord_id(node_id: str) -> str | None:
    with open(os.getenv("GITHUB_ID_TO_DISCORD_ID_MAPPING_PATH", "github_id_to_discord_id_mapping.yaml")) as file:
        mapping: dict[str, str] = yaml.load("".join(file.readlines()), Loader=yaml.Loader)

        if mapping is None:
            return None

        return mapping.get(node_id, None)


async def fetch_forum_channel(client: RESTClientImpl, forum_channel_id: int) -> GuildForumChannel | None:
    forum_channel = await client.fetch_channel(forum_channel_id)
    if forum_channel is None or not isinstance(forum_channel, GuildForumChannel):
        return None
    return forum_channel


def get_new_tag(new_tag_name: str, available_tags: list[ForumTag]) -> ForumTag | None:
    new_tag = next((tag for tag in available_tags if tag.name == new_tag_name), None)
    return new_tag


def generate_signature(secret: str, payload: bytes) -> str:
    hash_object = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
    return f"sha256={hash_object.hexdigest()}"


def verify_secret(secret: str, payload: bytes, signature_header: str) -> bool:
    if not secret:
        return True
    expected_signature = generate_signature(secret, payload)
    return hmac.compare_digest(expected_signature, signature_header)
