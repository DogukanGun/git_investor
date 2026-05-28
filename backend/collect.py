"""Run a one-off collection from the command line.

Usage: python collect.py [min_stars] [max_stars]
"""

import asyncio
import sys

from app.db import init_db
from app.collector import run_collection


def main() -> None:
    min_stars = int(sys.argv[1]) if len(sys.argv) > 1 else None
    max_stars = int(sys.argv[2]) if len(sys.argv) > 2 else None
    init_db()
    summary = asyncio.run(run_collection(min_stars, max_stars))
    print(f"Done: {summary}")


if __name__ == "__main__":
    main()
