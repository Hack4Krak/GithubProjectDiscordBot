from unittest.mock import patch

import pytest
from fastapi import HTTPException

from src.server import process_edition
from src.utils.data_types import (
    ProjectItemEditedAssignees,
    ProjectItemEditedBody,
    ProjectItemEditedSingleSelect,
    ProjectItemEditedTitle,
    SingleSelectType,
)


async def test_process_edition_body_changes():
    body = {"changes": {"body": {"to": "We need to pet more cats"}}}
    item_name = "PetSomeCats"
    expected_object = ProjectItemEditedBody(item_name, "Unknown", "We need to pet more cats")

    assert await process_edition(body, item_name) == expected_object


async def test_process_edition_body_no_changes():
    body = {}
    item_name = "Idk"

    with pytest.raises(HTTPException) as exception:
        await process_edition(body, item_name)
    assert exception.value.status_code == 400
    assert exception.value.detail == "Failed to recognize the edited event."


@patch("src.server.fetch_assignees")
async def test_process_edition_assignees_changed(mock_fetch_assignees):
    body = {"changes": {"field_value": {"field_type": "assignees"}}, "projects_v2_item": {"node_id": "node_id"}}
    item_name = "YouKnowIntegrationTestsAreNextDontYou?"
    new_assignees = ["Kubaryt", "Salieri", "Aniela"]
    mock_fetch_assignees.return_value = new_assignees
    expected_object = ProjectItemEditedAssignees(item_name, "Unknown", new_assignees)

    assert await process_edition(body, item_name) == expected_object


@patch("src.server.fetch_item_name")
async def test_process_edition_title_changed(mock_fetch_item_name):
    body = {"changes": {"field_value": {"field_type": "title"}}, "projects_v2_item": {"node_id": "node_id"}}
    item_name = "ImagineMockingDiscordSoMuchFun"
    new_item_name = "ActuallyNotFunAtAll"
    mock_fetch_item_name.return_value = new_item_name
    expected_object = ProjectItemEditedTitle(item_name, "Unknown", new_item_name)

    assert await process_edition(body, item_name) == expected_object


async def test_process_edition_single_select_changed():
    body = {
        "changes": {
            "field_value": {"field_type": "single_select", "field_name": "Size", "to": {"name": "Smol like lil kitten"}}
        },
        "projects_v2_item": {"node_id": "node_id"},
    }
    item_name = "Lil puppy"
    expected_object = ProjectItemEditedSingleSelect(item_name, "Unknown", "Smol like lil kitten", SingleSelectType.SIZE)

    assert await process_edition(body, item_name) == expected_object


async def test_process_edition_iteration_changed():
    new_title = "1.0.0 - FinallyWeShipItAfter25Years"
    body = {
        "changes": {"field_value": {"field_type": "iteration", "to": {"title": new_title}}},
        "projects_v2_item": {"node_id": "node_id"},
    }
    item_name = "Create Dockerfile for production"
    expected_object = ProjectItemEditedSingleSelect(item_name, "Unknown", new_title, SingleSelectType.ITERATION)

    assert await process_edition(body, item_name) == expected_object
