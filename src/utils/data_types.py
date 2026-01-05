from dataclasses import dataclass
from enum import Enum
from typing import Literal

from hikari import ForumTag, GuildForumChannel, GuildPublicThread
from hikari.impl import RESTClientImpl
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import PydanticCustomError

from src.utils.discord_rest_client import fetch_forum_channel, get_new_tag
from src.utils.error import ForumChannelNotFound
from src.utils.misc import SharedForumChannel, bot_logger, retrieve_discord_id


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
    # Used for appending link to Discord post
    item_id: int
    # Used for request to GitHub API
    node_id: str
    sender: str

    async def process(
        self,
        user_text_mention: str,
        post: GuildPublicThread,
        client: RESTClientImpl,
        shared_forum_channel: SharedForumChannel,
        forum_channel_id: int,
    ) -> str | GuildForumChannel | None:
        """
        Interface method to process the event and optionally return message to be posted in Discord.
        """


class SimpleProjectItemEvent(ProjectItemEvent):
    def __init__(self, item_id: int, node_id: str, sender: str, action_type: str):
        super().__init__(item_id, node_id, sender)
        self.event_type = SimpleProjectItemEventType(action_type)

    async def process(
        self,
        user_text_mention: str,
        post: GuildPublicThread,
        client: RESTClientImpl,
        _shared_forum_channel: SharedForumChannel,
        _forum_channel_id: int,
    ) -> str | None:
        match self.event_type:
            case SimpleProjectItemEventType.ARCHIVED:
                message = f"Task zarchiwizowany przez: {user_text_mention}."
                await client.edit_channel(post.id, archived=True)
                bot_logger.info(f"Post {self.node_id} archived.")
                return message
            case SimpleProjectItemEventType.RESTORED:
                message = f"Task przywrócony przez: {user_text_mention}."
                await client.edit_channel(post.id, archived=False)
                bot_logger.info(f"Post {self.node_id} restored.")
                return message
            case SimpleProjectItemEventType.DELETED:
                await client.delete_channel(post.id)
                bot_logger.info(f"Post {self.node_id} deleted.")
                return None
            case _:
                return None


class ProjectItemEditedBody(ProjectItemEvent):
    def __init__(self, item_id: int, node_id: str, editor: str, new_body: str):
        super().__init__(item_id, node_id, editor)
        self.new_body = new_body

    async def process(
        self,
        user_text_mention: str,
        _post: GuildPublicThread,
        client: RESTClientImpl,
        _shared_forum_channel: SharedForumChannel,
        forum_channel_id: int,
    ) -> str:
        message = f"Opis taska zaktualizowany przez: {user_text_mention}. Nowy opis: \n{self.new_body}"
        bot_logger.info(f"Post {self.node_id} body updated.")

        return message


class ProjectItemEditedAssignees(ProjectItemEvent):
    def __init__(self, item_id: int, node_id: str, editor: str, new_assignees: list[str]):
        super().__init__(item_id, node_id, editor)
        self.new_assignees = new_assignees

    async def process(
        self,
        user_text_mention: str,
        post: GuildPublicThread,
        client: RESTClientImpl,
        _shared_forum_channel: SharedForumChannel,
        forum_channel_id: int,
    ) -> None:
        assignee_mentions: list[str] = []
        assignee_discord_ids: list[int] = []
        if self.new_assignees:
            for assignee in self.new_assignees:
                discord_id = retrieve_discord_id(assignee)
                if discord_id:
                    assignee_mentions.append(f"<@{discord_id}>")
                    assignee_discord_ids.append(int(discord_id))
        else:
            assignee_mentions.append("Brak przypisanych osób")

        message = f"Osoby przypisane do taska edytowane, aktualni przypisani: {', '.join(assignee_mentions)}"
        await client.create_message(post.id, message, user_mentions=assignee_discord_ids)
        bot_logger.info(f"Post {self.node_id} assignees updated.")


class ProjectItemEditedTitle(ProjectItemEvent):
    def __init__(self, item_id: int, node_id: str, editor: str, new_name: str):
        super().__init__(item_id, node_id, editor)
        self.new_title = new_name

    async def process(
        self,
        user_text_mention: str,
        post: GuildPublicThread,
        client: RESTClientImpl,
        _shared_forum_channel: SharedForumChannel,
        forum_channel_id: int,
    ) -> None:
        await client.edit_channel(post.id, name=self.new_title)
        bot_logger.info(f"Post {self.node_id} title updated to {self.new_title}.")


class ProjectItemEditedSingleSelect(ProjectItemEvent):
    def __init__(self, item_id: int, node_id: str, editor: str, new_value: str, field_name: str):
        super().__init__(item_id, node_id, editor)
        self.new_value = new_value
        self.value_type = SingleSelectType(field_name)

    async def process(
        self,
        user_text_mention: str,
        post: GuildPublicThread,
        client: RESTClientImpl,
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
            bot_logger.info(f"Tag {new_tag_name} not found, creating new tag.")
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
        bot_logger.info(f"Post {self.node_id} tag updated to {new_tag_name}.")


class ProjectItemEditedDate(ProjectItemEvent):
    def __init__(self, item_id: int, node_id: str, editor: str, new_date: str):
        super().__init__(item_id, node_id, editor)
        self.new_date = new_date

    async def process(
        self,
        user_text_mention: str,
        post: GuildPublicThread,
        client: RESTClientImpl,
        _shared_forum_channel: SharedForumChannel,
        forum_channel_id: int,
    ) -> str:
        message = f"Data zadania zaktualizowana przez: {user_text_mention}. Nowa data: {self.new_date}"
        bot_logger.info(f"Post {self.node_id} date updated.")

        return message


class ProjectV2Item(BaseModel):
    item_id: int = Field(alias="id")
    node_id: str
    project_node_id: str

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
    field_type: Literal["assignees", "title", "single_select", "iteration", "date"]
    to: FieldValueTo | str | None = None
    field_name: str

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def check_iteration_and_date_must_have_to(self):
        if self.field_type in ["iteration", "date"] and self.to is None:
            raise PydanticCustomError(
                "missing_to",
                "'to' must be provided in field_value when field_type is 'date' or 'iteration'",
            )
        elif self.field_type == "date" and type(self.to) is not str:
            raise PydanticCustomError(
                "invalid_to",
                "'to' must be a string representing the date when field_type is 'date'",
            )
        elif self.field_type == "iteration" and not isinstance(self.to, FieldValueTo):
            raise PydanticCustomError(
                "invalid_to",
                "'to' must be an FieldValueTo object when field_type is 'iteration'",
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
