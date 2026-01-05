from unittest.mock import AsyncMock, patch

import pytest

from src.server import process_action, process_edition
from src.utils.data_types import (
    Body,
    Changes,
    FieldValue,
    FieldValueTo,
    ProjectItemEditedAssignees,
    ProjectItemEditedBody,
    ProjectItemEditedDate,
    ProjectItemEditedSingleSelect,
    ProjectItemEditedTitle,
    ProjectV2Item,
    Sender,
    SimpleProjectItemEvent,
    WebhookRequest,
)


@pytest.fixture
def mock_webhook_request_model():
    projects_v2_item = ProjectV2Item(id=1, project_node_id="node_id", node_id="node_id")
    sender = Sender(node_id="node_id")
    return WebhookRequest(
        projects_v2_item=projects_v2_item, action="edited", sender=sender, changes=Changes(body=Body(to="placeholder"))
    )


async def test_process_edition_body_changes(mock_webhook_request_model):
    mock_webhook_request_model.changes = Changes(body=Body(to="We need to pet more cats"))
    expected_object = ProjectItemEditedBody(1, "node_id", "node_id", "We need to pet more cats")

    assert await process_edition(mock_webhook_request_model) == expected_object


@patch("src.server.fetch_assignees")
async def test_process_edition_assignees_changed(mock_fetch_assignees, mock_webhook_request_model):
    mock_webhook_request_model.changes = Changes(field_value=FieldValue(field_name="Assignees", field_type="assignees"))
    new_assignees = ["Kubaryt", "Salieri", "Aniela"]
    mock_fetch_assignees.return_value = new_assignees
    expected_object = ProjectItemEditedAssignees(1, "node_id", "node_id", new_assignees)

    assert await process_edition(mock_webhook_request_model) == expected_object


@patch("src.server.fetch_item_name")
async def test_process_edition_title_changed(mock_fetch_item_name, mock_webhook_request_model):
    mock_webhook_request_model.changes = Changes(field_value=FieldValue(field_name="Title", field_type="title"))
    new_item_name = "ActuallyNotFunAtAll"
    mock_fetch_item_name.return_value = new_item_name
    expected_object = ProjectItemEditedTitle(1, "node_id", "node_id", new_item_name)

    assert await process_edition(mock_webhook_request_model) == expected_object


async def test_process_edition_single_select_changed(mock_webhook_request_model):
    mock_webhook_request_model.changes = Changes(
        field_value=FieldValue(
            field_name="Size", field_type="single_select", to=FieldValueTo(name="Smol like lil kitten")
        )
    )
    expected_object = ProjectItemEditedSingleSelect(1, "node_id", "node_id", "Smol like lil kitten", "Size")

    assert await process_edition(mock_webhook_request_model) == expected_object


async def test_process_edition_iteration_changed(mock_webhook_request_model):
    new_title = "1.0.0 - FinallyWeShipItAfter25Years"
    mock_webhook_request_model.changes = Changes(
        field_value=FieldValue(field_name="Iteration", field_type="iteration", to=FieldValueTo(title=new_title))
    )
    expected_object = ProjectItemEditedSingleSelect(1, "node_id", "node_id", new_title, "Iteration")

    assert await process_edition(mock_webhook_request_model) == expected_object


async def test_process_edition_date_changed(mock_webhook_request_model):
    mock_webhook_request_model.changes = Changes(
        field_value=FieldValue(field_name="Date", field_type="date", to="2024-12-31T23:59:59Z")
    )
    expected_object = ProjectItemEditedDate(1, "node_id", "node_id", "2024-12-31")

    assert await process_edition(mock_webhook_request_model) == expected_object


@patch("src.server.process_edition", new_callable=AsyncMock)
async def test_process_action_process_edition(mock_process_edition, mock_webhook_request_model):
    test_event = SimpleProjectItemEvent(1, "node_id", "node_id", "created")
    mock_process_edition.return_value = test_event

    assert await process_action(mock_webhook_request_model) == test_event


@patch("src.server.process_edition", new_callable=AsyncMock)
async def test_process_action_simple_event(mock_process_edition, mock_webhook_request_model):
    mock_webhook_request_model.action = "created"
    test_event = SimpleProjectItemEvent(1, "node_id", "node_id", "created")
    mock_process_edition.return_value = test_event

    assert await process_action(mock_webhook_request_model) == test_event
