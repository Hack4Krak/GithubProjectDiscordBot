from dataclasses import dataclass
from enum import Enum


class SimpleProjectItemEventType(Enum):
    CREATED = "created"
    ARCHIVED = "archived"
    RESTORED = "restored"
    DELETED = "deleted"


class SingleSelectType(Enum):
    STATUS = "Status"
    PRIORITY = "Priority"
    SIZE = "Size"
    ITERATION = "Iteration"
    SECTION = "Section"


def single_select_type_from_field_name(field_name: str | None) -> SingleSelectType | None:
    match field_name:
        case "Status":
            return SingleSelectType.STATUS
        case "Priority":
            return SingleSelectType.PRIORITY
        case "Size":
            return SingleSelectType.SIZE
        case "Iteration":
            return SingleSelectType.ITERATION
        case "Section":
            return SingleSelectType.SECTION
        case _:
            return None


@dataclass
class ProjectItemEvent:
    name: str
    sender: str


class SimpleProjectItemEvent(ProjectItemEvent):
    def __init__(self, name: str, sender: str, event_type: SimpleProjectItemEventType):
        super().__init__(name, sender)
        self.event_type = event_type


def simple_project_item_from_action_type(action_type: str, name: str, sender: str):
    match action_type:
        case "created":
            return SimpleProjectItemEvent(name, sender, SimpleProjectItemEventType.CREATED)
        case "archived":
            return SimpleProjectItemEvent(name, sender, SimpleProjectItemEventType.ARCHIVED)
        case "restored":
            return SimpleProjectItemEvent(name, sender, SimpleProjectItemEventType.RESTORED)
        case "deleted":
            return SimpleProjectItemEvent(name, sender, SimpleProjectItemEventType.DELETED)
        case _:
            raise ValueError(f"Unknown action type: {action_type}")


class ProjectItemEdited(ProjectItemEvent):
    pass


class ProjectItemEditedBody(ProjectItemEdited):
    def __init__(self, name: str, editor: str, new_body: str):
        super().__init__(name, editor)
        self.new_body = new_body


class ProjectItemEditedAssignees(ProjectItemEdited):
    def __init__(self, name: str, editor: str, new_assignees: list[str]):
        super().__init__(name, editor)
        self.new_assignees = new_assignees


class ProjectItemEditedTitle(ProjectItemEdited):
    def __init__(self, name: str, editor: str, new_name: str):
        super().__init__(name, editor)
        self.new_title = new_name


class ProjectItemEditedSingleSelect(ProjectItemEdited):
    def __init__(self, name: str, editor: str, new_value: str, value_type: SingleSelectType):
        super().__init__(name, editor)
        self.new_value = new_value
        self.value_type = value_type
