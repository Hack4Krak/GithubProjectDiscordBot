import asyncio
import os
from hikari import GuildForumChannel, GuildPublicThread, ForumTag, RESTApp
from copy import deepcopy


from src.utils.data_types import (
    ProjectItemEditedAssignees,
    ProjectItemEditedBody,
    ProjectItemEditedSingleSelect,
    ProjectItemEditedTitle,
    ProjectItemEvent,
    SimpleProjectItemEvent,
)
from src.utils.error import ForumChannelNotFound
from src.utils.utils import get_post_id, retrieve_discord_id

async def run(state: dict[str, bool | list[ProjectItemEvent]]):
    discord_rest = RESTApp()
    await discord_rest.start()

    async with discord_rest.acquire(os.getenv("DISCORD_TOKEN")) as client:
        forum_channel_id = int(os.getenv("FORUM_CHANNEL_ID"))
        forum_channel = await client.fetch_channel(forum_channel_id)
        if forum_channel is None or not isinstance(forum_channel, GuildForumChannel):
            raise ForumChannelNotFound(f"Forum channel with ID {forum_channel_id} not found.")

        if state["update-received"]:
            local_queue_copy: list[ProjectItemEvent] = deepcopy(state["update-queue"])
            state["update-queue"].clear()
            state["update-received"] = False

            for event in local_queue_copy:
                post_id = await get_post_id(event.name, forum_channel_id, client)
                author_discord_id = retrieve_discord_id(event.sender)
                if post_id is None:
                    message = f"Nowy task stworzony {event.name} przez <@{author_discord_id}>"
                    post: GuildPublicThread = await client.create_forum_post(forum_channel, event.name, message, auto_archive_duration=10080)
                else:
                    post = await client.fetch_channel(post_id)

                if not isinstance(post, GuildPublicThread):
                    continue

                if isinstance(event, SimpleProjectItemEvent):
                    match event.event_type.value:
                        case "archived":
                            message = f"Task zarchiwizowany przez <@{author_discord_id}>."
                            await client.create_message(post.id, message)
                            await client.edit_channel(post.id, archived=True)
                        case "restored":
                            message = f"Task przywrócony przez <@{author_discord_id}>."
                            await client.create_message(post.id, message)
                            await client.edit_channel(post.id, archived=False)
                        case "deleted":
                            await client.delete_channel(post.id)
                elif isinstance(event, ProjectItemEditedAssignees):
                    assignee_mentions: list[str] = []
                    if event.new_assignees:
                        for assignee in event.new_assignees:
                            discord_id = retrieve_discord_id(assignee)
                            if discord_id:
                                assignee_mentions.append(f"<@{discord_id}>")
                    else:
                        assignee_mentions.append("Brak przypisanych osób")

                    message = (
                        f"Osoby przypisane do taska edytowane, aktualni przypisani: {', '.join(assignee_mentions)}"
                    )
                    await client.create_message(post.id, message)
                elif isinstance(event, ProjectItemEditedBody):
                    message = f"Opis taska zaktualizowany przez <@{author_discord_id}>. Nowy opis: {event.new_body}"
                    await client.create_message(post.id, message)
                elif isinstance(event, ProjectItemEditedTitle):
                    await client.edit_channel(post.id, name=event.new_title)
                elif isinstance(event, ProjectItemEditedSingleSelect):
                    current_tag_ids = list(post.applied_tag_ids)
                    available_tags = list(forum_channel.available_tags)

                    for tag in available_tags:
                        if tag.id in current_tag_ids and tag.name.startswith(f"{event.value_type.value}: "):
                            current_tag_ids.remove(tag.id)

                    new_tag_name = f"{event.value_type.value}: {event.new_value}"
                    new_tag = next(
                        (tag for tag in available_tags if tag.name == new_tag_name),
                        None
                    )

                    if new_tag is None:
                        new_tag = ForumTag(name=new_tag_name)
                        await client.edit_channel(forum_channel.id, available_tags=available_tags.append(new_tag))

                    current_tag_ids.append(new_tag.id)

                    await client.edit_channel(post.id, applied_tag_ids=current_tag_ids)

            local_queue_copy.clear()

            await asyncio.sleep(1)