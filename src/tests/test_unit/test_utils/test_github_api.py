from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from src.utils import github_api


@patch("src.utils.github_api.send_request", new_callable=AsyncMock)
async def test_fetch_item_name_success(mock_send_request):
    mock_send_request.return_value = {"data": {"node": {"content": {"title": "42"}}}}

    assert await github_api.fetch_item_name("<node_id>") == "42"


@patch("src.utils.github_api.send_request", new_callable=AsyncMock)
async def test_fetch_item_name_partial(mock_send_request):
    mock_send_request.return_value = {"data": {"node": {"content": None}}}

    with pytest.raises(HTTPException) as exception:
        await github_api.fetch_item_name("<node_id>")

    assert exception.value.status_code == 500
    assert exception.value.detail == "Could not fetch item name."


@patch("src.utils.github_api.send_request", new_callable=AsyncMock)
async def test_fetch_item_name_none(mock_send_request):
    mock_send_request.return_value = {}

    with pytest.raises(HTTPException) as exception:
        await github_api.fetch_item_name("<node_id>")
    assert exception.value.status_code == 500
    assert exception.value.detail == "Could not fetch item name."


@patch("src.utils.github_api.send_request", new_callable=AsyncMock)
async def test_fetch_assignees_success(mock_send_request):
    mock_send_request.return_value = {
        "data": {
            "node": {
                "content": {"assignees": {"nodes": [{"id": "MDQ6VXNlcjg4MjY4MDYz"}, {"id": "MDQ6VXNlcjg5ODM3NzI0"}]}}
            }
        }
    }

    assert await github_api.fetch_assignees("<node_id>") == ["MDQ6VXNlcjg4MjY4MDYz", "MDQ6VXNlcjg5ODM3NzI0"]


@patch("src.utils.github_api.send_request", new_callable=AsyncMock)
async def test_fetch_assignees_partial(mock_send_request):
    mock_send_request.return_value = {"data": {"node": {"content": None}}}

    assert await github_api.fetch_assignees("<node_id>") == []


@patch("src.utils.github_api.send_request", new_callable=AsyncMock)
async def test_fetch_assignees_none(mock_send_request):
    mock_send_request.return_value = {}

    assert await github_api.fetch_assignees("<node_id>") == []


@patch("src.utils.github_api.send_request", new_callable=AsyncMock)
async def test_fetch_single_select_value_success(mock_send_request):
    mock_send_request.return_value = {"data": {"node": {"fieldValueByName": {"name": "Dziengiel"}}}}

    assert await github_api.fetch_single_select_value("<node_id>", "Salieri") == "Dziengiel"


@patch("src.utils.github_api.send_request", new_callable=AsyncMock)
async def test_fetch_single_select_value_partial(mock_send_request):
    mock_send_request.return_value = {"data": {"node": {"fieldValueByName": None}}}

    assert await github_api.fetch_single_select_value("<node_id>", "Salieri") is None


@patch("src.utils.github_api.send_request", new_callable=AsyncMock)
async def test_fetch_single_select_value_none(mock_send_request):
    mock_send_request.return_value = {}

    assert await github_api.fetch_single_select_value("<node_id>", "Salieri") is None
