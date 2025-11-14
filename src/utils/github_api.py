import os

import aiohttp


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
