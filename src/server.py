import os

from fastapi import FastAPI, HTTPException, Request
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHttpException
from starlette.responses import JSONResponse

from src.main import lifespan
from src.utils import get_item_name, verify_secret
from src.utils.data_types import (
    ProjectItemEdited,
    ProjectItemEditedAssignees,
    ProjectItemEditedBody,
    ProjectItemEditedSingleSelect,
    ProjectItemEditedTitle,
    SimpleProjectItemEvent,
    WebhookRequest,
)
from src.utils.github_api import fetch_assignees, fetch_item_name, fetch_single_select_value

app = FastAPI(lifespan=lifespan)


@app.exception_handler(StarletteHttpException)
async def http_exception_handler(_request: Request, exception: StarletteHttpException) -> JSONResponse:
    app.logger.error(f"HTTP exception occurred: {exception.detail}")
    return JSONResponse(status_code=exception.status_code, content={"detail": exception.detail})


@app.exception_handler(ValidationError)
async def validation_exception_handler(_request: Request, exception: ValidationError) -> JSONResponse:
    app.logger.error(
        f"ValidationError occurred: {exception.errors(include_url=False, include_context=False, include_input=False)}"
    )
    try:
        return JSONResponse(
            status_code=400,
            content={
                "detail": "Invalid request body.",
                "validation_errors": exception.errors(include_url=False, include_context=False, include_input=False),
            },
        )
    except TypeError:
        # Can happen when there is error in JSON parsing
        return JSONResponse(status_code=400, content={"detail": "Invalid request body."})


@app.exception_handler(Exception)
async def default_exception_handler(_request: Request, exception: Exception) -> JSONResponse:
    app.logger.error(f"Unhandled exception occurred: {str(exception)}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


@app.post("/webhook_endpoint")
async def webhook_endpoint(request: Request) -> JSONResponse:
    body_bytes = await request.body()
    if not body_bytes:
        raise HTTPException(status_code=400, detail="Missing request body.")
    signature = request.headers.get("X-Hub-Signature-256")
    if signature:
        correct_signature = verify_secret(os.getenv("GITHUB_WEBHOOK_SECRET", ""), body_bytes, signature)
        if not correct_signature:
            raise HTTPException(status_code=401, detail="Invalid signature.")
    elif os.getenv("GITHUB_WEBHOOK_SECRET", ""):
        raise HTTPException(status_code=401, detail="Missing signature.")
    else:
        app.logger.warning("No signature provided and no secret set; skipping verification.")

    body = WebhookRequest.model_validate_json(body_bytes)

    if body.projects_v2_item.project_node_id != os.getenv("GITHUB_PROJECT_NODE_ID"):
        raise HTTPException(status_code=400, detail="Invalid project_node_id.")

    item_name = await get_item_name(body.projects_v2_item.node_id)

    if body.action == "edited":
        project_item_event = await process_edition(body, item_name)
    else:
        project_item_event = SimpleProjectItemEvent(item_name, body.sender.node_id, body.action)

    await app.update_queue.put(project_item_event)

    app.logger.info(f"Received webhook event for item: {item_name}")
    return JSONResponse(content={"detail": "Successfully received webhook data"})


async def process_edition(body: WebhookRequest, item_name: str) -> ProjectItemEdited:
    editor = body.sender.node_id
    body_changed = body.changes.body

    if body_changed is not None:
        project_item_edited = ProjectItemEditedBody(item_name, editor, body_changed.to)
        return project_item_edited

    field_changed = body.changes.field_value

    if field_changed is None:
        raise HTTPException(status_code=400, detail="Failed to recognize the edited event.")

    match field_changed.field_type:
        case "assignees":
            new_assignees = await fetch_assignees(body.projects_v2_item.node_id)
            project_item_edited = ProjectItemEditedAssignees(item_name, editor, new_assignees)
            return project_item_edited
        case "title":
            new_title = await fetch_item_name(body.projects_v2_item.node_id)
            project_item_edited = ProjectItemEditedTitle(item_name, editor, new_title)
            return project_item_edited
        case "single_select":
            new_value = field_changed.to.name
            field_name = field_changed.field_name
            if new_value is None:
                new_value = await fetch_single_select_value(body.projects_v2_item.node_id, field_name)
            project_item_edited = ProjectItemEditedSingleSelect(item_name, editor, new_value, field_name)
            return project_item_edited
        case "iteration":
            new_value = field_changed.to.title
            project_item_edited = ProjectItemEditedSingleSelect(item_name, editor, new_value, "Iteration")
            return project_item_edited
