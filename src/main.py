import os

import dotenv
import uvicorn


def main():
    dotenv.load_dotenv()
    host, port = os.getenv("IP_ADDRESS", "0.0.0.0"), os.getenv("PORT", "8000")
    uvicorn.run("src.server:app", host=host, port=int(port), reload=True)


if __name__ == "__main__":
    main()
