import pytest

from src.utils import data_types
from src.utils.data_types import SimpleProjectItemEventType, SingleSelectType


def test_action_type_to_event_type():
    assert data_types.SimpleProjectItemEvent.action_type_to_event_type("created") == SimpleProjectItemEventType.CREATED
    assert (
        data_types.SimpleProjectItemEvent.action_type_to_event_type("archived") == SimpleProjectItemEventType.ARCHIVED
    )
    assert (
        data_types.SimpleProjectItemEvent.action_type_to_event_type("restored") == SimpleProjectItemEventType.RESTORED
    )
    assert data_types.SimpleProjectItemEvent.action_type_to_event_type("deleted") == SimpleProjectItemEventType.DELETED
    with pytest.raises(ValueError):
        data_types.SimpleProjectItemEvent.action_type_to_event_type("unknown")


def test_field_name_to_event_type():
    assert data_types.ProjectItemEditedSingleSelect.field_name_to_value_type("Status") == SingleSelectType.STATUS
    assert data_types.ProjectItemEditedSingleSelect.field_name_to_value_type("Priority") == SingleSelectType.PRIORITY
    assert data_types.ProjectItemEditedSingleSelect.field_name_to_value_type("Size") == SingleSelectType.SIZE
    assert data_types.ProjectItemEditedSingleSelect.field_name_to_value_type("Iteration") == SingleSelectType.ITERATION
    assert data_types.ProjectItemEditedSingleSelect.field_name_to_value_type("Section") == SingleSelectType.SECTION

    with pytest.raises(ValueError):
        data_types.ProjectItemEditedSingleSelect.field_name_to_value_type("Unknown")
