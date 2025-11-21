from unittest.mock import patch

import pytest

from src.server import process_edition
from src.utils.data_types import (
    Body,
    Changes,
    FieldValue,
    FieldValueTo,
    ProjectItemEditedAssignees,
    ProjectItemEditedBody,
    ProjectItemEditedSingleSelect,
    ProjectItemEditedTitle,
    ProjectV2Item,
    Sender,
    SingleSelectType,
    WebhookRequest,
)


@pytest.fixture
def mock_webhook_request_model():
    projects_v2_item = ProjectV2Item(project_node_id="node_id", node_id="node_id")
    sender = Sender(node_id="node_id")
    return WebhookRequest(
        projects_v2_item=projects_v2_item, action="edited", sender=sender, changes=Changes(body=Body(to="placeholder"))
    )


async def test_process_edition_body_changes(mock_webhook_request_model):
    mock_webhook_request_model.changes = Changes(body=Body(to="We need to pet more cats"))
    item_name = "PetSomeCats"
    expected_object = ProjectItemEditedBody(item_name, "node_id", "We need to pet more cats")

    assert await process_edition(mock_webhook_request_model, item_name) == expected_object


@patch("src.server.fetch_assignees")
async def test_process_edition_assignees_changed(mock_fetch_assignees, mock_webhook_request_model):
    mock_webhook_request_model.changes = Changes(field_value=FieldValue(field_name="Assignees", field_type="assignees"))
    item_name = "YouKnowIntegrationTestsAreNextDontYou?"
    new_assignees = ["Kubaryt", "Salieri", "Aniela"]
    mock_fetch_assignees.return_value = new_assignees
    expected_object = ProjectItemEditedAssignees(item_name, "node_id", new_assignees)

    assert await process_edition(mock_webhook_request_model, item_name) == expected_object


@patch("src.server.fetch_item_name")
async def test_process_edition_title_changed(mock_fetch_item_name, mock_webhook_request_model):
    mock_webhook_request_model.changes = Changes(field_value=FieldValue(field_name="Title", field_type="title"))
    item_name = "ImagineMockingDiscordSoMuchFun"
    new_item_name = "ActuallyNotFunAtAll"
    mock_fetch_item_name.return_value = new_item_name
    expected_object = ProjectItemEditedTitle(item_name, "node_id", new_item_name)

    assert await process_edition(mock_webhook_request_model, item_name) == expected_object


async def test_process_edition_single_select_changed(mock_webhook_request_model):
    mock_webhook_request_model.changes = Changes(
        field_value=FieldValue(
            field_name="Size", field_type="single_select", to=FieldValueTo(name="Smol like lil kitten")
        )
    )
    item_name = "Lil puppy"
    expected_object = ProjectItemEditedSingleSelect(item_name, "node_id", "Smol like lil kitten", SingleSelectType.SIZE)

    assert await process_edition(mock_webhook_request_model, item_name) == expected_object


async def test_process_edition_iteration_changed(mock_webhook_request_model):
    new_title = "1.0.0 - FinallyWeShipItAfter25Years"
    mock_webhook_request_model.changes = Changes(
        field_value=FieldValue(field_name="Iteration", field_type="iteration", to=FieldValueTo(title=new_title))
    )
    item_name = "Create Dockerfile for production"
    expected_object = ProjectItemEditedSingleSelect(item_name, "node_id", new_title, SingleSelectType.ITERATION)

    assert await process_edition(mock_webhook_request_model, item_name) == expected_object
