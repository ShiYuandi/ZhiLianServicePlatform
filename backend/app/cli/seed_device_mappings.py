from __future__ import annotations

import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from app.db.session import get_session_factory
from app.models.device_mapping import DeviceMapping


async def seed() -> int:
    seed_file = Path(__file__).resolve().parents[1] / "seeds" / "device_mappings.json"
    entries = json.loads(seed_file.read_text(encoding="utf-8"))
    inserted = 0
    async with get_session_factory()() as db:
        for entry in entries:
            exists = await db.scalar(
                select(DeviceMapping.id).where(DeviceMapping.name == entry["name"])
            )
            if exists:
                continue
            db.add(
                DeviceMapping(
                    name=entry["name"], agent_id=entry["agentId"], enabled=True
                )
            )
            inserted += 1
        await db.commit()
    return inserted


if __name__ == "__main__":
    count = asyncio.run(seed())
    print(f"seeded {count} device mappings")
