from __future__ import annotations

import asyncio

try:
    from src.charms_agent.agent import main
except ModuleNotFoundError:
    from charms_agent.agent import main


if __name__ == "__main__":
    asyncio.run(main())
