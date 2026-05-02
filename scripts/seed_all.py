"""
Combined seed runner — users then demo leads.

Usage:
    python -m scripts.seed_all
    python scripts/seed_all.py
"""

import asyncio

from scripts.seed_users import main as seed_users
from scripts.seed_demo_leads import main as seed_leads


async def run() -> None:
    await seed_users()
    await seed_leads()


if __name__ == "__main__":
    asyncio.run(run())
