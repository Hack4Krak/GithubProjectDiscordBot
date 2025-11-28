import asyncio
import logging
from io import StringIO
from unittest.mock import mock_open, patch

from src.utils import misc


@patch("builtins.open", new_callable=mock_open, read_data='MDQ6VXNlcjY2NTE0ODg1: "393756120952602625"')
@patch("yaml.load")
def test_retrieve_discord_id_present_id(mock_yaml_load, _mock_open_file):
    mock_yaml_load.return_value = {"MDQ6VXNlcjY2NTE0ODg1": "393756120952602625"}

    assert misc.retrieve_discord_id("MDQ6VXNlcjY2NTE0ODg1") == "393756120952602625"


@patch("builtins.open", new_callable=mock_open, read_data="")
def test_retrieve_discord_id_absent_id(_mock_open_file):
    assert misc.retrieve_discord_id("<node_id>") is None


def test_bot_logger_prefix():
    stream = StringIO()

    logger = misc.get_bot_logger()
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.handlers.clear()
    logger.addHandler(handler)

    logger.info("hello")

    output = stream.getvalue().strip()
    assert output == "INFO [BOT] hello"


async def test_shared_forum_channel_concurrent_readers(shared_forum_channel_mock):
    started = asyncio.Event()
    completed = []

    async def reader(reader_id):
        async with shared_forum_channel_mock.lock.reader_lock:
            await started.wait()
            completed.append(reader_id)

    tasks = [asyncio.create_task(reader(i)) for i in range(5)]
    started.set()
    await asyncio.gather(*tasks)

    assert sorted(completed) == [0, 1, 2, 3, 4]


async def test_shared_forum_channel_writer_blocks_readers(shared_forum_channel_mock):
    enter_order = []

    async def writer():
        async with shared_forum_channel_mock.lock.writer_lock:
            enter_order.append("writer")
            await asyncio.sleep(0.1)

    async def reader():
        async with shared_forum_channel_mock.lock.reader_lock:
            enter_order.append("reader")

    writer_task = asyncio.create_task(writer())

    reader_task = asyncio.create_task(reader())
    await asyncio.gather(writer_task, reader_task)

    assert enter_order == ["writer", "reader"]


async def test_shared_forum_channel_writers_are_exclusive(shared_forum_channel_mock):
    execution = []

    async def writer(writer_id):
        async with shared_forum_channel_mock.lock.writer_lock:
            execution.append(writer_id)
            await asyncio.sleep(0.05)

    t1 = asyncio.create_task(writer(1))
    t2 = asyncio.create_task(writer(2))

    await asyncio.gather(t1, t2)

    assert execution == [1, 2] or execution == [2, 1]
    assert execution[0] != execution[1]
