import asyncio
import os
from contextlib import asynccontextmanager

import dotenv
import uvicorn
from fastapi import FastAPI

from src.bot import run
from src.utils.misc import server_logger


def main():
    dotenv.load_dotenv()
    host, port = os.getenv("IP_ADDRESS", "0.0.0.0"), os.getenv("PORT", "8000")
    uvicorn.run("src.server:app", host=host, port=int(port), reload=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    app.update_queue = asyncio.Queue()
    task = asyncio.create_task(run(app.update_queue))
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
        server_logger.error(f"Bot task crashed: {exception}")


if __name__ == "__main__":
    main()
