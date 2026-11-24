"""Async example, keyless: two lookups at the same time. Run: python examples/async_example.py"""

import asyncio

from mygeocode import AsyncClient


async def main() -> None:
    async with AsyncClient() as client:
        tokyo, everest = await asyncio.gather(
            client.timezone(35.6762, 139.6503),
            client.elevation(27.9881, 86.9250),
        )
        print(tokyo.timezone, tokyo.utc_offset, everest.results[0].elevation_m)


loop = asyncio.new_event_loop()  # asyncio.run() is newer than Python 3.6
try:
    loop.run_until_complete(main())
finally:
    loop.close()
