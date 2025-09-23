import asyncio
import os
from copy import deepcopy
from threading import Lock

import discord

from src.utils.data_types import (
    ProjectItemEditedAssignees,
    ProjectItemEditedBody,
    ProjectItemEditedSingleSelect,
    ProjectItemEditedTitle,
    ProjectItemEvent,
    SimpleProjectItemEvent,
)
from src.utils.error import ForumChannelNotFound
from src.utils.utils import add_tag_to_thread, get_post_id, retrieve_discord_id


class DiscordClient(discord.Client):
    bg_task: asyncio.Task

    def __init__(self, *, state, lock, **kwargs):
        super().__init__(**kwargs)
        self.state: dict[str, bool | list[ProjectItemEvent]] = state
        self.lock: Lock = lock

    async def on_ready(self):
        print(f"Logged on as {self.user}!")
        self.bg_task = self.loop.create_task(self.process_updates())

    async def process_updates(self):
        forum_channel_id = int(os.getenv("FORUM_CHANNEL_ID"))
        forum_channel: discord.ForumChannel = self.get_channel(forum_channel_id)
        if forum_channel is None:
            raise ForumChannelNotFound(f"Forum channel with ID {forum_channel_id} not found.")
        local_queue_copy: list[ProjectItemEvent] = []

        while True:
            with self.lock:
                if self.state["update-received"]:
                    local_queue_copy = deepcopy(self.state["update-queue"])
                    self.state["update-queue"].clear()
                    self.state["update-received"] = False

            for event in local_queue_copy:
                post_id = await get_post_id(event.name, forum_channel)
                author_discord_id = retrieve_discord_id(event.sender)
                if post_id is None:
                    message = f"Nowy task stworzony {event.name} przez <@{author_discord_id}>"
                    await forum_channel.create_thread(name=event.name, content=message, auto_archive_duration=10080)
                    post_id = await get_post_id(event.name, forum_channel)
                thread: discord.Thread = forum_channel.get_thread(int(post_id)) or await self.fetch_channel(
                    int(post_id)
                )
                if thread is None:
                    continue

                if isinstance(event, SimpleProjectItemEvent):
                    match event.event_type.value:
                        case "archived":
                            message = f"Task zarchiwizowany przez <@{author_discord_id}>."
                            await thread.send(message)
                            await thread.edit(archived=True)
                        case "restored":
                            message = f"Task przywrócony przez <@{author_discord_id}>."
                            await thread.send(message)
                            await thread.edit(archived=False)
                        case "deleted":
                            await thread.delete()
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
                    await thread.send(message)
                elif isinstance(event, ProjectItemEditedBody):
                    message = f"Opis taska zaktualizowany przez <@{author_discord_id}>. Nowy opis: {event.new_body}"
                    await thread.send(message)
                elif isinstance(event, ProjectItemEditedTitle):
                    await thread.edit(name=event.new_title)
                elif isinstance(event, ProjectItemEditedSingleSelect):
                    thread_tags = list(thread.applied_tags)
                    for tag in thread_tags:
                        if tag.name.startswith(f"{event.value_type.value}: "):
                            await thread.remove_tags(tag)

                    await add_tag_to_thread(
                        thread, forum_channel, f"{event.value_type.value}: {event.new_value}", event.value_type.value
                    )

            local_queue_copy.clear()

            await asyncio.sleep(1)


def run(state, lock):
    intents = discord.Intents.default()

    client = DiscordClient(intents=intents, state=state, lock=lock)
    client.run(os.getenv("DISCORD_BOT_TOKEN"))
