from __future__ import annotations

import asyncio
import copy
import json
import sys
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from clients.base import BaseExchangeClient, BaseRestClient
from core.config_loader import load_app_config
from core.engine import HedgeEngine


class SnapshotConfig:
    def __init__(self, config):
        self._config = config

    def snapshot(self):
        return copy.deepcopy(self._config)


class AuditGateClient(BaseExchangeClient):
    def __init__(self, account_name: str, runtime, positions: dict[tuple[str, str], Decimal], orders: list[dict[str, Any]]):
        super().__init__(runtime)
        self.name = account_name
        self.positions = positions
        self.orders = orders

    async def get_position(self, symbol: str, **kwargs):
        return self.positions.get((self.name, symbol), Decimal("0"))

    async def ensure_margin_settings(self, symbol: str, leverage=None, margin_mode=None, **kwargs):
        return {"ok": True, "symbol": symbol, "leverage": leverage, "margin_mode": margin_mode}

    async def adjust_position(
        self,
        symbol: str,
        delta,
        *,
        current=None,
        target=None,
        leverage=None,
        min_qty=None,
        step=None,
        max_adjust_qty=None,
        reduce_only: bool = False,
        settle: str | None = None,
        **kwargs,
    ):
        delta = Decimal(str(delta))
        qty = abs(delta)
        if max_adjust_qty is not None and qty > Decimal(str(max_adjust_qty)):
            qty = Decimal(str(max_adjust_qty))
        if step is not None:
            qty = self.quantize_down(qty, Decimal(str(step)))
        if min_qty is not None:
            qty = self.ensure_min_qty(qty, Decimal(str(min_qty)))
        if qty == 0:
            return {"ok": True, "skipped": True, "reason": "below_min_qty"}

        signed_size = qty if delta > 0 else -qty
        payload = {
            "account": self.name,
            "exchange": "gate",
            "symbol": symbol,
            "side": "BUY" if delta > 0 else "SELL",
            "qty": str(qty),
            "signed_size": str(signed_size),
            "current": str(current),
            "target": str(target),
            "delta": str(delta),
            "settle": settle or kwargs.get("settle"),
            "dry_run": True,
        }
        self.orders.append(payload)
        return {"ok": True, "dry_run": True, "payload": payload}


class AuditWebseaClient(BaseRestClient):
    def __init__(self, account_name: str, runtime, positions: dict[tuple[str, str], Decimal], orders: list[dict[str, Any]]):
        super().__init__(runtime)
        self.name = account_name
        self.positions = positions
        self.orders = orders

    async def get_position(self, symbol: str, **kwargs):
        return self.positions.get((self.name, symbol), Decimal("0"))

    async def ensure_margin_settings(self, symbol: str, leverage=None, margin_mode=None, **kwargs):
        return {"ok": True, "symbol": symbol, "leverage": leverage, "margin_mode": "cross"}

    async def _place_contract_order(self, *, symbol: str, contract_type: str, side: str, qty, leverage=None, price=None):
        qty_dec = Decimal(str(qty))
        if qty_dec <= 0:
            return {"ok": True, "skipped": True, "reason": "non_positive_qty"}

        payload = {
            "account": self.name,
            "exchange": "websea",
            "symbol": symbol,
            "contract_type": contract_type,
            "type": "buy-market" if side.upper() == "BUY" else "sell-market",
            "side": side.upper(),
            "qty": str(qty_dec),
            "leverage": leverage,
            "is_full": 2,
            "dry_run": True,
        }
        self.orders.append(payload)
        return {"ok": True, "dry_run": True, "payload": payload}

    async def adjust_position(
        self,
        symbol: str,
        delta,
        *,
        current=None,
        target=None,
        leverage=None,
        min_qty=None,
        step=None,
        max_adjust_qty=None,
        reduce_only: bool = False,
        **kwargs,
    ):
        current = Decimal(str(current if current is not None else "0"))
        target = Decimal(str(target if target is not None else current + Decimal(str(delta))))
        delta = Decimal(str(delta))

        def normalize(qty: Decimal) -> Decimal:
            q = abs(qty)
            if max_adjust_qty is not None and q > Decimal(str(max_adjust_qty)):
                q = Decimal(str(max_adjust_qty))
            if step is not None:
                q = self.quantize_down(q, Decimal(str(step)))
            if min_qty is not None:
                q = self.ensure_min_qty(q, Decimal(str(min_qty)))
            return q

        if delta == 0:
            return {"ok": True, "skipped": True, "reason": "zero_delta"}

        if current == 0 or target == 0 or (current > 0 and target > 0) or (current < 0 and target < 0):
            qty = normalize(delta)
            if qty == 0:
                return {"ok": True, "skipped": True, "reason": "below_min_qty"}
            side = "BUY" if delta > 0 else "SELL"
            contract_type = "close" if reduce_only else "open"
            if current > 0 and target >= 0 and delta < 0:
                contract_type = "close"
                side = "SELL"
            elif current < 0 and target <= 0 and delta > 0:
                contract_type = "close"
                side = "BUY"
            elif current >= 0 and target > current and delta > 0:
                contract_type = "open"
                side = "BUY"
            elif current <= 0 and target < current and delta < 0:
                contract_type = "open"
                side = "SELL"
            return await self._place_contract_order(
                symbol=symbol,
                contract_type=contract_type,
                side=side,
                qty=qty,
                leverage=leverage,
            )

        responses = []
        close_qty = normalize(current)
        if close_qty > 0:
            responses.append(await self._place_contract_order(
                symbol=symbol,
                contract_type="close",
                side="SELL" if current > 0 else "BUY",
                qty=close_qty,
                leverage=leverage,
            ))
        open_qty = normalize(target)
        if open_qty > 0:
            responses.append(await self._place_contract_order(
                symbol=symbol,
                contract_type="open",
                side="BUY" if target > 0 else "SELL",
                qty=open_qty,
                leverage=leverage,
            ))
        return {"ok": True, "split": True, "responses": responses}


def expected_targets(unit, rule, source_size: Decimal):
    rows = []
    for member in unit.source.followers:
        if member.enabled:
            rows.append({
                "account": member.account,
                "exchange": unit.source.exchange,
                "symbol": rule.source_symbol,
                "target": source_size * member.ratio,
            })

    hedge_target = source_size * rule.ratio * unit.hedge.ratio
    if str(unit.hedge.mode).lower() == "opposite":
        hedge_target = -hedge_target
    rows.append({
        "account": unit.hedge.account,
        "exchange": unit.hedge.exchange,
        "symbol": rule.hedge_symbol,
        "target": hedge_target,
    })
    for member in unit.hedge.followers:
        if member.enabled:
            rows.append({
                "account": member.account,
                "exchange": unit.hedge.exchange,
                "symbol": rule.hedge_symbol,
                "target": hedge_target * member.ratio,
            })
    return rows


async def run_audit():
    config = load_app_config("config")
    config.runtime.dry_run = True
    config.telegram["enabled"] = False
    cfg_mgr = SnapshotConfig(config)
    engine = HedgeEngine(cfg_mgr)
    engine._runtime = config.runtime
    engine._sync_semaphore = asyncio.Semaphore(max(1, int(config.runtime.max_concurrent_adjustments)))

    unit = config.units[0]
    source_sizes = {
        "BTC_USDT": Decimal("20"),
        "ETH_USDT": Decimal("2"),
        "SOL_USDT": Decimal("1"),
    }

    positions: dict[tuple[str, str], Decimal] = {}
    orders: list[dict[str, Any]] = []
    sync_records: list[dict[str, Any]] = []
    used_accounts = engine._collect_used_accounts(config)
    for account_name in used_accounts:
        account = config.accounts[account_name]
        if account.exchange == "gate":
            engine._clients[account_name] = AuditGateClient(account_name, config.runtime, positions, orders)
        elif account.exchange == "websea":
            engine._clients[account_name] = AuditWebseaClient(account_name, config.runtime, positions, orders)

    async def record_last_sync(account_name: str, symbol: str, payload: dict):
        sync_records.append({
            "account": account_name,
            "symbol": symbol,
            **payload,
        })

    engine._record_last_sync = record_last_sync

    report = []
    for rule in unit.symbols:
        if not rule.enabled:
            continue
        source_size = source_sizes.get(rule.source_symbol, Decimal("2"))
        before = len(orders)
        before_records = len(sync_records)
        await engine._sync_update({
            "unit_name": unit.name,
            "symbol": rule.source_symbol,
            "size": source_size,
            "raw": {"contract": rule.source_symbol, "size": str(source_size)},
        })
        after_orders = orders[before:]
        after_records = sync_records[before_records:]
        expected = expected_targets(unit, rule, source_size)
        report.append({
            "unit": unit.name,
            "source_symbol": rule.source_symbol,
            "hedge_symbol": rule.hedge_symbol,
            "source_master_position": str(source_size),
            "expected_targets": [
                {**row, "target": str(row["target"])}
                for row in expected
            ],
            "orders": after_orders,
            "sync_records": after_records,
        })
    return report


def main():
    report = asyncio.run(run_audit())
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
