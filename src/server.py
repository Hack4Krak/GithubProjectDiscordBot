import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request

from src.bot import run
from src.utils.data_types import (
    ProjectItemEdited,
    ProjectItemEditedAssignees,
    ProjectItemEditedBody,
    ProjectItemEditedSingleSelect,
    ProjectItemEditedTitle,
    ProjectItemEvent,
    SingleSelectType,
    simple_project_item_from_action_type,
    single_select_type_from_field_name,
)
from src.utils.utils import fetch_assignees, fetch_item_name, fetch_single_select_value, get_item_name


state: dict[str, bool | list[ProjectItemEvent]] = {"update-received": False, "update-queue": []}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    task = asyncio.create_task(run(state))
    yield
    # shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan)

@app.post("/webhook_endpoint")
async def webhook_endpoint(request: Request):
    body: dict[str, Any] = await request.json()
    projects_v2_item: dict[str, Any] = body.get("projects_v2_item", {})
    if not projects_v2_item:
        return
    project_node_id: str | None = projects_v2_item.get("project_node_id", None)
    if project_node_id is None or project_node_id != os.getenv("GITHUB_PROJECT_NODE_ID"):
        return

    item_node_id: str | None = projects_v2_item.get("node_id", None)
    if item_node_id is None:
        return
    item_name = await get_item_name(item_node_id)
    if item_name is None:
        return

    if body["action"] == "edited":
        project_item_event = await process_edition(body, item_name)
    else:
        project_item_event = simple_project_item_from_action_type(
            body["action"], item_name, body.get("sender", {}).get("login", "Unknown")
        )

    if project_item_event is not None:
        state["update-queue"].append(project_item_event)
        state["update-received"] = True

    return


async def process_edition(body: dict[str, Any], item_name: str) -> ProjectItemEdited | None:
    editor: str = body.get("sender").get("login", "Unknown")
    body_changed: dict[str, Any] | None = body.get("changes", {}).get("body", None)

    if body_changed is not None:
        new_body = body_changed.get("to", "")
        project_item_edited = ProjectItemEditedBody(item_name, editor, new_body)
        return project_item_edited

    field_changed: dict[str, Any] | None = body.get("changes", {}).get("field_value", None)

    if field_changed is None:
        return None

    match field_changed["field_type"]:
        case "assignees":
            new_assignees = await fetch_assignees(body.get("projects_v2_item", {}).get("node_id", None))
            project_item_edited = ProjectItemEditedAssignees(item_name, editor, new_assignees)
            return project_item_edited
        case "title":
            new_title = await fetch_item_name(body.get("projects_v2_item", {}).get("node_id", None))
            project_item_edited = ProjectItemEditedTitle(item_name, editor, new_title)
            return project_item_edited
        case "single_select":
            new_value: str | None = field_changed.get("to", {}).get("name", None)
            if new_value is None:
                new_value = fetch_single_select_value(
                    body.get("projects_v2_item", {}).get("node_id", None), field_changed.get("field_name", None)
                )
            value_type = single_select_type_from_field_name(field_changed.get("field_name", None))
            project_item_edited = ProjectItemEditedSingleSelect(item_name, editor, new_value, value_type)
            return project_item_edited
        case "iteration":
            new_value = field_changed.get("to", {}).get("title", None)
            project_item_edited = ProjectItemEditedSingleSelect(
                item_name, editor, new_value, SingleSelectType.ITERATION
            )
            return project_item_edited

    return None
