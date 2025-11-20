import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from json import JSONDecodeError
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from starlette.exceptions import HTTPException as StarletteHttpException
from starlette.responses import JSONResponse

from src.bot import run
from src.utils import get_item_name, verify_secret
from src.utils.data_types import (
    ProjectItemEdited,
    ProjectItemEditedAssignees,
    ProjectItemEditedBody,
    ProjectItemEditedSingleSelect,
    ProjectItemEditedTitle,
    SingleSelectType,
    simple_project_item_from_action_type,
    single_select_type_from_field_name,
)
from src.utils.github_api import fetch_assignees, fetch_item_name, fetch_single_select_value


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    app.update_queue = asyncio.Queue()
    app.logger = logging.getLogger("uvicorn.error")
    task = asyncio.create_task(run(app.update_queue, app.logger))
    task.add_done_callback(handle_task_exception)
    yield
    # shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def handle_task_exception(task: asyncio.Task):
    try:
        exception = task.exception()
    except asyncio.CancelledError:
        return

    if exception:
        app.logger.error(f"Bot task crashed: {exception}")


app = FastAPI(lifespan=lifespan)


@app.exception_handler(StarletteHttpException)
async def http_exception_handler(_request: Request, exception: StarletteHttpException) -> JSONResponse:
    app.logger.error(f"HTTP exception occurred: {exception.detail}")
    return JSONResponse(status_code=exception.status_code, content={"detail": exception.detail})


@app.exception_handler(KeyError)
async def key_error_exception_handler(_request: Request, exception: KeyError) -> JSONResponse:
    app.logger.error(f"KeyError occurred: {str(exception)}")
    return JSONResponse(status_code=400, content={"detail": f"Missing property in body: {str(exception)}"})


@app.exception_handler(Exception)
async def default_exception_handler(_request: Request, exception: Exception) -> JSONResponse:
    app.logger.error(f"Unhandled exception occurred: {str(exception)}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


@app.post("/webhook_endpoint")
async def webhook_endpoint(request: Request) -> JSONResponse:
    body_bytes = await request.body()
    if not body_bytes:
        return JSONResponse(status_code=400, content={"detail": "Missing request body."})
    signature = request.headers.get("X-Hub-Signature-256")
    if signature:
        correct_signature = verify_secret(os.getenv("GITHUB_WEBHOOK_SECRET", ""), body_bytes, signature)
        if not correct_signature:
            raise HTTPException(status_code=401, detail="Invalid signature.")
    elif os.getenv("GITHUB_WEBHOOK_SECRET", ""):
        raise HTTPException(status_code=401, detail="Missing signature.")
    else:
        app.logger.warning("No signature provided and no secret set; skipping verification.")
    try:
        body: dict[str, Any] = json.loads(body_bytes)
    except JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.") from None
    projects_v2_item: dict[str, Any] = body["projects_v2_item"]
    project_node_id: str | None = projects_v2_item["project_node_id"]
    if project_node_id != os.getenv("GITHUB_PROJECT_NODE_ID"):
        raise HTTPException(status_code=400, detail="Invalid project_node_id.")

    item_node_id: str | None = projects_v2_item["node_id"]
    item_name = await get_item_name(item_node_id)

    if body.get("action") == "edited":
        project_item_event = await process_edition(body, item_name)
    elif body.get("action") is not None:
        project_item_event = simple_project_item_from_action_type(
            body["action"], item_name, body.get("sender", {}).get("node_id", "Unknown")
        )
    else:
        raise HTTPException(status_code=400, detail="Missing action in payload.")

    await app.update_queue.put(project_item_event)

    app.logger.info(f"Received webhook event for item: {item_name}")
    return JSONResponse(content={"detail": "Successfully received webhook data"})


async def process_edition(body: dict[str, Any], item_name: str) -> ProjectItemEdited:
    editor: str = body.get("sender", {}).get("node_id", "Unknown")
    body_changed: dict[str, Any] | None = body.get("changes", {}).get("body", None)

    if body_changed is not None:
        new_body = body_changed.get("to", "")
        project_item_edited = ProjectItemEditedBody(item_name, editor, new_body)
        return project_item_edited

    field_changed: dict[str, Any] | None = body.get("changes", {}).get("field_value", None)

    if field_changed is None:
        raise HTTPException(status_code=400, detail="Failed to recognize the edited event.")

    node_id: str | None = body.get("projects_v2_item", {}).get("node_id", None)
    if node_id is None:
        raise HTTPException(status_code=400, detail="Missing item node ID.")

    match field_changed["field_type"]:
        case "assignees":
            new_assignees = await fetch_assignees(node_id)
            project_item_edited = ProjectItemEditedAssignees(item_name, editor, new_assignees)
            return project_item_edited
        case "title":
            new_title = await fetch_item_name(node_id)
            project_item_edited = ProjectItemEditedTitle(item_name, editor, new_title)
            return project_item_edited
        case "single_select":
            new_value: str | None = field_changed.get("to", {}).get("name", None)
            field_name: str | None = field_changed.get("field_name", None)
            if field_name is None:
                raise HTTPException(status_code=400, detail="Missing field name for single select field.")
            if new_value is None:
                new_value = await fetch_single_select_value(node_id, field_name)
            value_type = single_select_type_from_field_name(field_name)
            if value_type is None:
                raise HTTPException(status_code=400, detail=f"Unknown single select field name: {field_name}")
            project_item_edited = ProjectItemEditedSingleSelect(item_name, editor, new_value, value_type)
            return project_item_edited
        case "iteration":
            new_value = field_changed.get("to", {}).get("title", None)
            if new_value is None:
                raise HTTPException(status_code=400, detail="Missing new value for iteration field.")
            project_item_edited = ProjectItemEditedSingleSelect(
                item_name, editor, new_value, SingleSelectType.ITERATION
            )
            return project_item_edited

    raise HTTPException(status_code=400, detail=f"Unknown field type: {field_changed['field_type']}")
