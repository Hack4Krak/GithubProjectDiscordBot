import os

import dotenv
import uvicorn


def main():
    dotenv.load_dotenv()
    host, port = os.getenv("IP_ADDRESS", "0.0.0.0:8000").split(":")
    uvicorn.run("src.server:src", host=host, port=int(port), reload=True)


if __name__ == "__main__":
    main()
