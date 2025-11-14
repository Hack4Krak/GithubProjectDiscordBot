import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

from src.bot import run
from src.utils import get_item_name, verify_secret
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
from src.utils.github_api import fetch_assignees, fetch_item_name, fetch_single_select_value
from src.utils.logging import server_error, server_info, server_warning

update_queue: asyncio.Queue[ProjectItemEvent] = asyncio.Queue()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    task = asyncio.create_task(run(update_queue))
    yield
    # shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan)


@app.post("/webhook_endpoint")
async def webhook_endpoint(request: Request) -> JSONResponse:
    body_bytes = await request.body()
    if not body_bytes:
        server_error("Received empty body in webhook request.")
        return JSONResponse(status_code=400, content={"detail": "Missing request body."})
    signature = request.headers.get("X-Hub-Signature-256")
    if signature:
        correct_signature = verify_secret(os.getenv("GITHUB_WEBHOOK_SECRET", ""), body_bytes, signature)
        if not correct_signature:
            server_error("Invalid signature in webhook request.")
            return JSONResponse(status_code=401, content={"detail": "Invalid signature"})
    elif os.getenv("GITHUB_WEBHOOK_SECRET", ""):
        server_error("Missing signature in webhook request.")
        return JSONResponse(status_code=401, content={"detail": "Missing signature"})
    else:
        server_warning(
            "Signature verification is disabled. To enable it set the 'GITHUB_WEBHOOK_SECRET' environment variable."
        )
    try:
        body: dict[str, Any] = json.loads(body_bytes)
    except json.JSONDecodeError:
        server_error("Invalid JSON data in webhook request.")
        return JSONResponse(status_code=400, content={"detail": "Invalid JSON data."})
    projects_v2_item: dict[str, Any] = body.get("projects_v2_item", {})
    if not projects_v2_item:
        server_error("Missing projects_v2_item in webhook payload.")
        return JSONResponse(status_code=400, content={"detail": "Missing projects_v2_item in payload."})
    project_node_id: str | None = projects_v2_item.get("project_node_id", None)
    if project_node_id is None or project_node_id != os.getenv("GITHUB_PROJECT_NODE_ID"):
        server_error("Invalid project_node_id in webhook payload.")
        return JSONResponse(status_code=400, content={"detail": "Invalid project_node_id."})

    item_node_id: str | None = projects_v2_item.get("node_id", None)
    if item_node_id is None:
        server_error("Missing item_node_id in webhook payload.")
        return JSONResponse(status_code=400, content={"detail": "Missing item_node_id in payload."})
    item_name = await get_item_name(item_node_id)
    if item_name is None:
        server_error("Could not fetch item name.")
        return JSONResponse(status_code=500, content={"detail": "Could not fetch item name."})

    if body.get("action") == "edited":
        project_item_event = await process_edition(body, item_name)
    elif body.get("action") is not None:
        project_item_event = simple_project_item_from_action_type(
            body["action"], item_name, body.get("sender", {}).get("node_id", "Unknown")
        )
    else:
        server_error("Missing action in webhook payload.")
        return JSONResponse(status_code=400, content={"detail": "Missing action in payload."})

    if project_item_event is not None:
        await update_queue.put(project_item_event)

    server_info(f"Received webhook for item: {item_name}")
    return JSONResponse(content={"detail": "Successfully received webhook data"})


async def process_edition(body: dict[str, Any], item_name: str) -> ProjectItemEdited | None:
    editor: str = body.get("sender", {}).get("node_id", "Unknown")
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
                new_value = await fetch_single_select_value(
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
