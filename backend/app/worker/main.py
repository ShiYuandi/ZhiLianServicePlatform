import asyncio

from app.core.config import get_settings
from app.worker.runner import run_forever


def main() -> None:
    asyncio.run(run_forever(get_settings()))


if __name__ == "__main__":
    main()
