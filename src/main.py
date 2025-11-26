import asyncio
import os
from contextlib import asynccontextmanager

import dotenv
import uvicorn
from fastapi import FastAPI

from src.bot import run
from src.utils.misc import handle_task_exception


def main():
    dotenv.load_dotenv()
    host, port = os.getenv("IP_ADDRESS", "0.0.0.0"), os.getenv("PORT", "8000")
    uvicorn.run("src.server:app", host=host, port=int(port), reload=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    app.update_queue = asyncio.Queue()
    bot_task = asyncio.create_task(run(app.update_queue))
    bot_task.add_done_callback(lambda task: handle_task_exception(task, "Bot task crashed:"))
    yield
    # shutdown
    bot_task.cancel()
    try:
        await bot_task
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    main()
