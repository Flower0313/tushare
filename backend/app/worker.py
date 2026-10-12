import asyncio

from app.runtime import run_worker


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
