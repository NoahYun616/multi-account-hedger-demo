from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import ssl
import time
from typing import Awaitable, Callable, List, Optional

import certifi
import websockets

from core.models import RuntimeConfig

logger = logging.getLogger("client.gate_ws")


class GatePositionsWatcher:
    def __init__(
        self,
        *,
        name: str,
        ws_url: str,
        api_key: str,
        api_secret: str,
        user_id: str,
        settle: str,
        symbols: List[str],
        runtime: RuntimeConfig,
        on_position: Callable[[dict], Awaitable[None]],
    ):
        self.name = name
        self.ws_url = ws_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.user_id = user_id
        self.settle = settle
        self.symbols = symbols
        self.runtime = runtime
        self.on_position = on_position
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()
        self._ssl_ctx = ssl.create_default_context(cafile=certifi.where())

    def _auth_sign(self, channel: str, event: str, time_: int) -> str:
        msg = f"channel={channel}&event={event}&time={time_}"
        return hmac.new(
            self.api_secret.encode("utf-8"),
            msg.encode("utf-8"),
            hashlib.sha512,
        ).hexdigest()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name=f"gate-ws-{self.name}")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _subscribe(self, ws, symbol: str) -> None:
        now = int(time.time())
        payload = {
            "time": now,
            "channel": "futures.positions",
            "event": "subscribe",
            "payload": [self.user_id, symbol],
            "auth": {
                "method": "api_key",
                "KEY": self.api_key,
                "SIGN": self._auth_sign("futures.positions", "subscribe", now),
            },
        }
        await ws.send(json.dumps(payload))

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                async with websockets.connect(
                    self.ws_url,
                    ssl=self._ssl_ctx,
                    ping_interval=self.runtime.ws_ping_interval,
                    ping_timeout=self.runtime.ws_ping_timeout,
                    max_queue=1000,
                ) as ws:
                    logger.info("gate ws connected | %s | %s", self.name, self.ws_url)
                    for symbol in self.symbols:
                        await self._subscribe(ws, symbol)

                    async for message in ws:
                        data = json.loads(message)
                        if data.get("channel") == "futures.positions" and data.get("event") == "update":
                            for row in data.get("result", []):
                                await self.on_position(row)

                        if self._stop.is_set():
                            break

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("gate ws reconnect | %s | %s", self.name, exc)
                await asyncio.sleep(self.runtime.reconnect_delay_sec)