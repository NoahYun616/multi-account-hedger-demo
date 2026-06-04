from __future__ import annotations

import logging
import time
from typing import Dict, Optional

import aiohttp


logger = logging.getLogger("telegram")


class TelegramNotifier:
    def __init__(self, token: str | None, chat_id: str | None, enabled: bool, cooldown_sec: int = 60):
        self.token = token
        self.chat_id = chat_id
        self.enabled = enabled and bool(token) and bool(chat_id)
        self.cooldown_sec = cooldown_sec
        self._last_sent: Dict[str, float] = {}

    async def send(self, key: str, text: str) -> None:
        if not self.enabled:
            return
        now = time.time()
        if now - self._last_sent.get(key, 0) < self.cooldown_sec:
            return
        self._last_sent[key] = now
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as resp:
                    if resp.status >= 300:
                        logger.warning("telegram alert failed: status=%s body=%s", resp.status, await resp.text())
        except Exception as exc:
            logger.warning("telegram alert exception: %s", exc)
