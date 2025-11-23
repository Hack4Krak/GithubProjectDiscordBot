from unittest.mock import patch

import pytest
from aiohttp import ClientSession
from fastapi import HTTPException

from src.tests.utils import MockResponse
from src.utils import github_api


@patch.object(ClientSession, "post")
async def test_fetch_item_name_success(mock_post_request):
    mock_response = {"data": {"node": {"content": {"title": "42"}}}}
    mock_post_request.return_value = MockResponse(mock_response)

    assert await github_api.fetch_item_name("<node_id>") == "42"


@patch.object(ClientSession, "post")
async def test_fetch_item_name_partial(mock_post_request):
    mock_response = {"data": {"node": {"content": None}}}
    mock_post_request.return_value = MockResponse(mock_response)

    with pytest.raises(HTTPException) as exception:
        await github_api.fetch_item_name("<node_id>")

    assert exception.value.status_code == 500
    assert exception.value.detail == "Could not fetch item name."


@patch.object(ClientSession, "post")
async def test_fetch_item_name_none(mock_post_request):
    mock_post_request.return_value = MockResponse({})

    with pytest.raises(HTTPException) as exception:
        await github_api.fetch_item_name("<node_id>")
    assert exception.value.status_code == 500
    assert exception.value.detail == "Could not fetch item name."


@patch.object(ClientSession, "post")
async def test_fetch_assignees_success(mock_post_request):
    mock_response = {
        "data": {
            "node": {
                "content": {"assignees": {"nodes": [{"id": "MDQ6VXNlcjg4MjY4MDYz"}, {"id": "MDQ6VXNlcjg5ODM3NzI0"}]}}
            }
        }
    }
    mock_post_request.return_value = MockResponse(mock_response)

    assert await github_api.fetch_assignees("<node_id>") == ["MDQ6VXNlcjg4MjY4MDYz", "MDQ6VXNlcjg5ODM3NzI0"]


@patch.object(ClientSession, "post")
async def test_fetch_assignees_partial(mock_post_request):
    mock_response = {"data": {"node": {"content": None}}}
    mock_post_request.return_value = MockResponse(mock_response)

    assert await github_api.fetch_assignees("<node_id>") == []


@patch.object(ClientSession, "post")
async def test_fetch_assignees_none(mock_post_request):
    mock_post_request.return_value = MockResponse({})

    assert await github_api.fetch_assignees("<node_id>") == []


@patch.object(ClientSession, "post")
async def test_fetch_single_select_value_success(mock_post_request):
    mock_response = {"data": {"node": {"fieldValueByName": {"name": "Dziengiel"}}}}
    mock_post_request.return_value = MockResponse(mock_response)

    assert await github_api.fetch_single_select_value("<node_id>", "Salieri") == "Dziengiel"


@patch.object(ClientSession, "post")
async def test_fetch_single_select_value_partial(mock_post_request):
    mock_response = {"data": {"node": {"fieldValueByName": None}}}
    mock_post_request.return_value = MockResponse(mock_response)

    assert await github_api.fetch_single_select_value("<node_id>", "Salieri") is None


@patch.object(ClientSession, "post")
async def test_fetch_single_select_value_none(mock_post_request):
    mock_response = {}
    mock_post_request.return_value = MockResponse(mock_response)

    assert await github_api.fetch_single_select_value("<node_id>", "Salieri") is None
