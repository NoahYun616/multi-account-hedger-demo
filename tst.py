import asyncio
import ssl
import certifi
import websockets

async def test():
    ctx = ssl.create_default_context(cafile=certifi.where())
    async with websockets.connect(
        "wss://fx-ws.gateio.ws/v4/ws/usdt",
        ssl=ctx,
        ping_interval=10,
        ping_timeout=10,
    ) as ws:
        print("WS OK")

asyncio.run(test())

import asyncio
import ssl
import certifi
import aiohttp

async def test():
    ctx = ssl.create_default_context(cafile=certifi.where())
    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=ctx)
    ) as session:
        async with session.get("https://oapi.websea.com/v1/futures/info?symbol=BTC-USDT", ssl=ctx) as resp:
            print(resp.status)
            print(await resp.text())

asyncio.run(test())