import os

import aiohttp
from fastapi import HTTPException


async def fetch_item_name(item_node_id: str) -> str:
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
    except TypeError, KeyError, AttributeError:
        raise HTTPException(status_code=500, detail="Could not fetch item name.") from None

    return item_name


async def fetch_assignees(item_node_id: str) -> list[str]:
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
    except TypeError, KeyError, AttributeError:
        return []
    assignees = [assignee.get("id", None) for assignee in assignees_data]

    return assignees


async def fetch_single_select_value(item_node_id: str, field_name: str) -> str | None:
    if field_name is None:
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
    except TypeError, KeyError, AttributeError:
        return None

    return name
