import datetime

import pytest
from hikari import (
    ChannelFlag,
    ForumLayoutType,
    ForumSortOrderType,
    ForumTag,
    GuildForumChannel,
    GuildPublicThread,
    PartialChannel,
    RESTAware,
    Snowflake,
    ThreadMetadata,
)
from hikari.impl import EntityFactoryImpl, HTTPSettings, ProxySettings, RESTClientImpl

from src.utils.misc import SharedForumChannel


class MockShelf(dict):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class MockResponse(dict):
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def json(self):
        return self


class RestClientContextManagerMock:
    rest_client_mock: RESTClientImpl

    def __init__(self, rest_client_mock):
        self.rest_client_mock = rest_client_mock

    async def __aenter__(self):
        return self.rest_client_mock

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def post_mock():
    return PartialChannel(app=RESTAware, id=Snowflake(621), name="audacity4", type=0)


@pytest.fixture
def rest_client_mock():
    entity_factory = EntityFactoryImpl(app=RESTAware)
    http_settings = HTTPSettings()
    proxy_settings = ProxySettings()
    return RESTClientImpl(
        cache=None,
        entity_factory=entity_factory,
        executor=None,
        http_settings=http_settings,
        proxy_settings=proxy_settings,
        token=None,
        token_type=None,
        rest_url=None,
    )


@pytest.fixture
def forum_channel_mock():
    mock_timedelta = datetime.timedelta(seconds=0)
    return GuildForumChannel(
        app=RESTAware,
        id=Snowflake(67),
        name="forum-channel",
        topic="A forum channel",
        is_nsfw=False,
        default_auto_archive_duration=mock_timedelta,
        available_tags=[ForumTag(id=Snowflake(1), name="Size: smol", moderated=False)],
        type=0,
        guild_id=Snowflake(41),
        parent_id=None,
        position=0,
        permission_overwrites={},
        last_thread_id=None,
        rate_limit_per_user=mock_timedelta,
        default_thread_rate_limit_per_user=mock_timedelta,
        flags=ChannelFlag(0),
        default_sort_order=ForumSortOrderType.CREATION_DATE,
        default_layout=ForumLayoutType.GALLERY_VIEW,
        default_reaction_emoji_id=None,
        default_reaction_emoji_name=None,
    )


@pytest.fixture
def shared_forum_channel_mock(forum_channel_mock):
    return SharedForumChannel(forum_channel_mock)


@pytest.fixture
def full_post_mock():
    mock_timedelta = datetime.timedelta(seconds=0)
    mock_datetime = datetime.datetime.now()
    mock_metadata = ThreadMetadata(
        is_archived=False,
        archive_timestamp=mock_datetime,
        auto_archive_duration=mock_timedelta,
        is_invitable=False,
        is_locked=False,
        created_at=mock_datetime,
    )
    return GuildPublicThread(
        app=RESTAware,
        id=Snowflake(621),
        name="audacity4",
        type=0,
        guild_id=Snowflake(0),
        last_message_id=None,
        last_pin_timestamp=None,
        rate_limit_per_user=mock_timedelta,
        approximate_message_count=0,
        approximate_member_count=0,
        member=None,
        owner_id=Snowflake(0),
        parent_id=Snowflake(0),
        metadata=mock_metadata,
        applied_tag_ids=[Snowflake(1)],
        flags=ChannelFlag(0),
    )


@pytest.fixture
def user_text_mention():
    return "<@123456789012345678>"
