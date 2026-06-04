from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from core.state_store import StateStore


class StateStoreTest(unittest.TestCase):
    def test_load_save_and_overwrite(self):
        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "state.json"
                store = StateStore(str(path))

                await store.load()
                await store.set_master_position("unit_1", "BTC_USDT", "12")
                await store.set_last_sync(
                    "gate_sub_1",
                    "BTC_USDT",
                    {"ok": True, "target": "12", "delta": "2"},
                )
                await store.save()

                raw = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(raw["master_positions"]["unit_1"]["BTC_USDT"], "12")
                self.assertEqual(raw["last_sync"]["gate_sub_1"]["BTC_USDT"]["target"], "12")

                loaded = StateStore(str(path))
                await loaded.load()
                await loaded.set_master_position("unit_1", "BTC_USDT", "15")
                await loaded.save()

                raw = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(raw["master_positions"]["unit_1"]["BTC_USDT"], "15")

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
