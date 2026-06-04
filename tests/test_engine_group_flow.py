from __future__ import annotations

import asyncio
import unittest
from decimal import Decimal

from core.engine import HedgeEngine
from core.models import AppConfig, Leg, Member, RuntimeConfig, SymbolRule, UnitConfig


class SnapshotConfig:
    def __init__(self, config):
        self._config = config

    def snapshot(self):
        return self._config


class FakeClient:
    def __init__(self, name, calls, *, fail=False):
        self.name = name
        self.calls = calls
        self.fail = fail

    async def get_position(self, symbol, **kwargs):
        if self.fail:
            raise RuntimeError(f"{self.name} failed")
        return Decimal("0")

    async def ensure_margin_settings(self, **kwargs):
        return {"ok": True}

    async def adjust_position(self, symbol, delta, **kwargs):
        self.calls.append({
            "account": self.name,
            "symbol": symbol,
            "delta": str(delta),
            "target": str(kwargs.get("target")),
        })
        return {"ok": True}


def make_engine(*, failing_accounts=()):
    runtime = RuntimeConfig(dry_run=True, max_concurrent_adjustments=5)
    unit = UnitConfig(
        name="unit_1",
        enabled=True,
        source=Leg(
            account="gate_master",
            exchange="gate",
            settle="usdt",
            followers=[
                Member(account="gate_sub_bad", ratio=Decimal("1"), enabled=True),
                Member(account="gate_sub_ok", ratio=Decimal("1"), enabled=True),
            ],
        ),
        hedge=Leg(
            account="websea_master",
            exchange="websea",
            mode="opposite",
            ratio=Decimal("1"),
            followers=[
                Member(account="websea_sub_ok", ratio=Decimal("1"), enabled=True),
            ],
        ),
        symbols=[
            SymbolRule(
                source_symbol="BTC_USDT",
                hedge_symbol="BTC-USDT",
                ratio=Decimal("1"),
                min_sync_delta=Decimal("0"),
                source_step=Decimal("1"),
                hedge_step=Decimal("1"),
                source_min_qty=Decimal("1"),
                hedge_min_qty=Decimal("1"),
            )
        ],
    )
    config = AppConfig(runtime=runtime, accounts={}, units=[unit], telegram={"enabled": False})
    engine = HedgeEngine(SnapshotConfig(config))
    engine._runtime = runtime
    engine._sync_semaphore = asyncio.Semaphore(runtime.max_concurrent_adjustments)

    calls = []
    records = []
    for account in ["gate_sub_bad", "gate_sub_ok", "websea_master", "websea_sub_ok"]:
        engine._clients[account] = FakeClient(
            account,
            calls,
            fail=account in set(failing_accounts),
        )

    async def record_last_sync(account_name, symbol, payload):
        records.append({"account": account_name, "symbol": symbol, **payload})

    async def alert(**kwargs):
        return None

    engine._record_last_sync = record_last_sync
    engine._alert = alert
    return engine, calls, records


class EngineGroupFlowTest(unittest.IsolatedAsyncioTestCase):
    async def test_sub_error_is_ignored_after_master_success(self):
        engine, calls, records = make_engine(failing_accounts={"gate_sub_bad"})

        await engine._sync_update({
            "unit_name": "unit_1",
            "symbol": "BTC_USDT",
            "size": Decimal("3"),
        })

        self.assertCountEqual(
            [item["account"] for item in calls],
            ["gate_sub_ok", "websea_master", "websea_sub_ok"],
        )
        bad_records = [item for item in records if item["account"] == "gate_sub_bad"]
        self.assertEqual(bad_records[0]["reason"], "sub_error_ignored")

    async def test_hedge_sub_is_skipped_when_hedge_master_fails(self):
        engine, calls, records = make_engine(failing_accounts={"websea_master"})

        await engine._sync_update({
            "unit_name": "unit_1",
            "symbol": "BTC_USDT",
            "size": Decimal("3"),
        })

        self.assertNotIn("websea_sub_ok", [item["account"] for item in calls])
        master_records = [item for item in records if item["account"] == "websea_master"]
        self.assertEqual(master_records[0]["reason"], "master_error")


if __name__ == "__main__":
    unittest.main()
