import asyncio
import logging
import os
from contextlib import asynccontextmanager

import dotenv
import uvicorn
from fastapi import FastAPI

from src.bot import run


def main():
    dotenv.load_dotenv()
    host, port = os.getenv("IP_ADDRESS", "0.0.0.0"), os.getenv("PORT", "8000")
    uvicorn.run("src.server:app", host=host, port=int(port), reload=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    app.update_queue = asyncio.Queue()
    app.logger = logging.getLogger("uvicorn.error")
    task = asyncio.create_task(run(app.update_queue))
    task.add_done_callback(lambda task: handle_task_exception(task, app))
    yield
    # shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def handle_task_exception(task: asyncio.Task, app: FastAPI):
    try:
        exception = task.exception()
    except asyncio.CancelledError:
        return

    if exception:
        app.logger.error(f"Bot task crashed: {exception}")


if __name__ == "__main__":
    main()
