from dataclasses import dataclass
from enum import Enum
from logging import Logger
from typing import Literal

from fastapi import HTTPException
from hikari import ForumTag, GuildForumChannel, GuildPublicThread
from hikari.impl import RESTClientImpl
from pydantic import BaseModel, ConfigDict, model_validator
from pydantic_core import PydanticCustomError

from src.utils.discord_rest_client import fetch_forum_channel, get_new_tag
from src.utils.error import ForumChannelNotFound
from src.utils.misc import SharedForumChannel, add_bot_log_prefix, retrieve_discord_id


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


@dataclass
class ProjectItemEvent:
    name: str
    sender: str

    async def process(
        self,
        user_text_mention: str,
        post: GuildPublicThread,
        client: RESTClientImpl,
        logger: Logger,
        shared_forum_channel: SharedForumChannel,
        forum_channel_id: int,
    ) -> str | GuildForumChannel | None:
        """
        Interface method to process the event and optionally return message to be posted in Discord.
        """


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

    async def process(
        self,
        user_text_mention: str,
        post: GuildPublicThread,
        client: RESTClientImpl,
        logger: Logger,
        _shared_forum_channel: SharedForumChannel,
        _forum_channel_id: int,
    ) -> str | None:
        match self.event_type.value:
            case "archived":
                message = f"Task zarchiwizowany przez: {user_text_mention}."
                await client.edit_channel(post.id, archived=True)
                logger.info(add_bot_log_prefix(f"Post {self.name} archived."))

                return message
            case "restored":
                message = f"Task przywrócony przez: {user_text_mention}."
                await client.edit_channel(post.id, archived=False)
                logger.info(add_bot_log_prefix(f"Post {self.name} restored."))
                return message
            case "deleted":
                await client.delete_channel(post.id)
                logger.info(add_bot_log_prefix(f"Post {self.name} deleted."))
                return None
            case _:
                return None


class ProjectItemEdited(ProjectItemEvent):
    pass


class ProjectItemEditedBody(ProjectItemEdited):
    def __init__(self, name: str, editor: str, new_body: str):
        super().__init__(name, editor)
        self.new_body = new_body

    async def process(
        self,
        user_text_mention: str,
        _post: GuildPublicThread,
        client: RESTClientImpl,
        logger: Logger,
        _shared_forum_channel: SharedForumChannel,
        forum_channel_id: int,
    ) -> str:
        message = f"Opis taska zaktualizowany przez: {user_text_mention}. Nowy opis: \n{self.new_body}"
        logger.info(add_bot_log_prefix(f"Post {self.name} body updated."))

        return message


class ProjectItemEditedAssignees(ProjectItemEdited):
    def __init__(self, name: str, editor: str, new_assignees: list[str]):
        super().__init__(name, editor)
        self.new_assignees = new_assignees

    async def process(
        self,
        user_text_mention: str,
        post: GuildPublicThread,
        client: RESTClientImpl,
        logger: Logger,
        _shared_forum_channel: SharedForumChannel,
        forum_channel_id: int,
    ) -> None:
        assignee_mentions: list[str] = []
        assignee_discord_ids: list[int] = []
        if self.new_assignees:
            for assignee in self.new_assignees:
                discord_id = retrieve_discord_id(assignee)
                assignee_discord_ids.append(int(discord_id)) if discord_id else None
                if discord_id:
                    assignee_mentions.append(f"<@{discord_id}>")
        else:
            assignee_mentions.append("Brak przypisanych osób")

        message = f"Osoby przypisane do taska edytowane, aktualni przypisani: {', '.join(assignee_mentions)}"
        await client.create_message(post.id, message, user_mentions=assignee_discord_ids)
        logger.info(add_bot_log_prefix(f"Post {self.name} assignees updated."))


class ProjectItemEditedTitle(ProjectItemEdited):
    def __init__(self, name: str, editor: str, new_name: str):
        super().__init__(name, editor)
        self.new_title = new_name

    async def process(
        self,
        user_text_mention: str,
        post: GuildPublicThread,
        client: RESTClientImpl,
        logger: Logger,
        _shared_forum_channel: SharedForumChannel,
        forum_channel_id: int,
    ) -> None:
        await client.edit_channel(post.id, name=self.new_title)
        logger.info(add_bot_log_prefix(f"Post {self.name} title updated to {self.new_title}."))


class ProjectItemEditedSingleSelect(ProjectItemEdited):
    def __init__(self, name: str, editor: str, new_value: str, field_name: str):
        super().__init__(name, editor)
        self.new_value = new_value
        match field_name:
            case "Status":
                value_type = SingleSelectType.STATUS
            case "Priority":
                value_type = SingleSelectType.PRIORITY
            case "Size":
                value_type = SingleSelectType.SIZE
            case "Iteration":
                value_type = SingleSelectType.ITERATION
            case "Section":
                value_type = SingleSelectType.SECTION
            case _:
                raise HTTPException(status_code=400, detail=f"Unknown single select field name: {field_name}")
        self.value_type = value_type

    async def process(
        self,
        user_text_mention: str,
        post: GuildPublicThread,
        client: RESTClientImpl,
        logger: Logger,
        shared_forum_channel: SharedForumChannel,
        forum_channel_id: int,
    ) -> None:
        async with shared_forum_channel.lock.reader_lock:
            available_tags = list(shared_forum_channel.forum_channel.available_tags)
        current_tag_ids = list(post.applied_tag_ids)

        for tag in available_tags:
            if tag.id in current_tag_ids and tag.name.startswith(f"{self.value_type.value}: "):
                current_tag_ids.remove(tag.id)

        new_tag_name = f"{self.value_type.value}: {self.new_value}"[:48]
        new_tag = get_new_tag(new_tag_name, available_tags)

        if new_tag is None:
            logger.info(add_bot_log_prefix(f"Tag {new_tag_name} not found, creating new tag."))
            await client.edit_channel(forum_channel_id, available_tags=[*available_tags, ForumTag(name=new_tag_name)])
            forum_channel = await fetch_forum_channel(client, forum_channel_id)
            if forum_channel is None:
                raise ForumChannelNotFound(f"Forum channel with ID {forum_channel_id} not found.")
            async with shared_forum_channel.lock.writer_lock:
                shared_forum_channel.forum_channel = forum_channel
            async with shared_forum_channel.lock.reader_lock:
                available_tags = list(shared_forum_channel.forum_channel.available_tags)
            new_tag = get_new_tag(new_tag_name, available_tags)

        current_tag_ids.append(new_tag.id)

        await client.edit_channel(post.id, applied_tags=current_tag_ids)
        logger.info(add_bot_log_prefix(f"Post {self.name} tag updated to {new_tag_name}."))


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
