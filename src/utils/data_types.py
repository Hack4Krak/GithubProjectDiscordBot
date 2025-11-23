from dataclasses import dataclass
from enum import Enum
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, model_validator
from pydantic_core import PydanticCustomError


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


def single_select_type_from_field_name(field_name: str) -> SingleSelectType | None:
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
    def __init__(self, name: str, sender: str, action_type: str):
        match action_type:
            case "created":
                event_type = SimpleProjectItemEventType.CREATED
            case "archived":
                event_type = SimpleProjectItemEventType.ARCHIVED
            case "restored":
                event_type = SimpleProjectItemEventType.RESTORED
            case "deleted":
                event_type = SimpleProjectItemEventType.DELETED
            case _:
                raise HTTPException(status_code=400, detail=f"Unknown action type: {action_type}")
        super().__init__(name, sender)
        self.event_type = event_type


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


class ProjectV2Item(BaseModel):
    project_node_id: str
    node_id: str

    model_config = ConfigDict(extra="allow")


class Sender(BaseModel):
    node_id: str

    model_config = ConfigDict(extra="allow")


class Body(BaseModel):
    to: str

    model_config = ConfigDict(extra="allow")


class FieldValueTo(BaseModel):
    name: str | None = None
    title: str | None = None

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def check_name_or_title(self):
        if self.name is None and self.title is None:
            raise PydanticCustomError(
                "missing_name_or_title",
                "either 'name' or 'title' must be provided in field_value.to",
            )
        return self


class FieldValue(BaseModel):
    field_type: Literal["assignees", "title", "single_select", "iteration"]
    to: FieldValueTo | None = None
    field_name: str

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def check_iteration_must_have_to(self):
        if self.field_type == "iteration" and self.to is None:
            raise PydanticCustomError(
                "missing_to",
                "'to' must be provided in field_value when field_type is 'single_select' or 'iteration'",
            )
        return self


class Changes(BaseModel):
    body: Body | None = None
    field_value: FieldValue | None = None

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def check_name_or_title(self):
        if self.body is None and self.field_value is None:
            raise PydanticCustomError(
                "missing_name_or_title",
                "either 'body' or 'field_value' must be provided in body.changes",
            )
        return self


class WebhookRequest(BaseModel):
    projects_v2_item: ProjectV2Item
    action: str
    sender: Sender
    changes: Changes | None = None

    @model_validator(mode="after")
    def changes_must_be_present_for_edited_action(self):
        if self.action == "edited" and self.changes is None:
            raise PydanticCustomError(
                "missing_changes",
                "'changes' must be provided in webhook request when action is 'edited'",
            )
        return self

    model_config = ConfigDict(extra="allow")
