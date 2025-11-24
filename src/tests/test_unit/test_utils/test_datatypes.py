import pytest

from src.utils.data_types import SimpleProjectItemEventType, SingleSelectType


def test_action_type_to_event_type():
    assert SimpleProjectItemEventType("created") == SimpleProjectItemEventType.CREATED
    assert SimpleProjectItemEventType("archived") == SimpleProjectItemEventType.ARCHIVED
    assert SimpleProjectItemEventType("restored") == SimpleProjectItemEventType.RESTORED
    assert SimpleProjectItemEventType("deleted") == SimpleProjectItemEventType.DELETED
    with pytest.raises(ValueError):
        SimpleProjectItemEventType("unknown")


def test_field_name_to_event_type():
    assert SingleSelectType("Status") == SingleSelectType.STATUS
    assert SingleSelectType("Priority") == SingleSelectType.PRIORITY
    assert SingleSelectType("Size") == SingleSelectType.SIZE
    assert SingleSelectType("Iteration") == SingleSelectType.ITERATION
    assert SingleSelectType("Section") == SingleSelectType.SECTION

    with pytest.raises(ValueError):
        SingleSelectType("Unknown")
