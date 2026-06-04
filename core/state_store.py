from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict


logger = logging.getLogger("state_store")


class StateStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self._lock = asyncio.Lock()
        self._state: Dict[str, Any] = {"master_positions": {}, "last_sync": {}}

    async def load(self) -> None:
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            return
        try:
            self._state = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("load state failed: %s", exc)

    async def save(self) -> None:
        async with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp_path.write_text(
                json.dumps(self._state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp_path.replace(self.path)

    async def set_master_position(self, strategy: str, symbol: str, size: str) -> None:
        self._state.setdefault("master_positions", {}).setdefault(strategy, {})[symbol] = size

    async def set_last_sync(self, account: str, symbol: str, payload: Dict[str, Any]) -> None:
        self._state.setdefault("last_sync", {}).setdefault(account, {})[symbol] = payload

    def snapshot(self) -> Dict[str, Any]:
        return self._state
