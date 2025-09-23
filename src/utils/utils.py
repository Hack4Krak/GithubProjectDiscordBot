import json
import os
import shelve

import requests
from discord import ForumChannel, ForumTag, Thread


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

    response = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": variables},
        headers={"Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}"},
    )

    item_name: str | None = response.json().get("data", {}).get("node", {}).get("content", {}).get("title", None)

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
                  login
                }
              }
            }
            ... on Issue {
              assignees(first: 10) {
                nodes {
                  login
                }
              }
            }
            ... on PullRequest {
              assignees(first: 10) {
                nodes {
                  login
                }
              }
            }
          }
        }
      }
    }
    """

    variables = {"id": item_node_id}

    response = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": variables},
        headers={"Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}"},
    )

    assignees_data = (
        response.json().get("data", {}).get("node", {}).get("content", {}).get("assignees", {}).get("nodes", {})
    )
    assignees = [assignee.get("login", {}) for assignee in assignees_data]

    return assignees


def fetch_single_select_value(item_node_id: str | None, field_name: str | None) -> str | None:
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

    response = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": variables},
        headers={"Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}"},
    )

    name: str | None = response.json().get("data", {}).get("node", {}).get("fieldValueByName", None).get("name", None)

    return name


async def get_post_id(name: str, forum_channel: ForumChannel) -> int | None:
    with shelve.open("post_id.db") as db:
        try:
            post_id: str = db[name]
            return int(post_id)
        except KeyError:
            pass
        for thread in forum_channel.threads:
            if thread.name == name:
                db[name] = thread.id
                return thread.id
        async for thread in forum_channel.archived_threads():
            if thread.name == name:
                db[name] = thread.id
                return thread.id

    return None


def retrieve_discord_id(username: str) -> str | None:
    with open(
        os.getenv("GITHUB_USERNAME_TO_DISCORD_ID_MAPPING_PATH", "github_usernames_to_discord_id_mapping.json")
    ) as file:
        mapping: dict[str, str] = json.loads("".join(file.readlines()))

        return mapping.get(username, None)


def get_tags_for_single_select_type(section: str, tags: list[ForumTag]) -> list[ForumTag]:
    tags_for_single_select_type: list[ForumTag] = []
    for tag in tags:
        if tag.name.startswith(section + ": "):
            tags_for_single_select_type.append(tag)

    return tags_for_single_select_type


async def add_tag_to_thread(thread: Thread, forum_channel: ForumChannel, tag_name: str, single_select_type: str):
    tags = get_tags_for_single_select_type(single_select_type, list(forum_channel.available_tags))
    for tag in tags:
        if tag.name == tag_name:
            await thread.add_tags(tag)
            return
    await forum_channel.create_tag(name=tag_name)
    await add_tag_to_thread(thread, forum_channel, tag_name, single_select_type)
