from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from clients.gate_rest import GateRestClient
from clients.gate_ws import GatePositionsWatcher
from clients.websea_rest import WebseaRestClient
from core.config_loader import ConfigManager
from core.models import AppConfig, Member, SymbolRule, UnitConfig
from core.state_store import StateStore
from notify.telegram_notifier import TelegramNotifier

logger = logging.getLogger("engine")


class HedgeEngine:
    def __init__(self, cfg_mgr: ConfigManager):
        self.cfg_mgr = cfg_mgr

        self._queue: asyncio.Queue = asyncio.Queue()
        self._stop = asyncio.Event()

        self._consume_task: Optional[asyncio.Task] = None
        self._reload_task: Optional[asyncio.Task] = None

        self._clients: Dict[str, Any] = {}
        self._client_errors: Dict[str, str] = {}
        self._watchers: List[Any] = []

        self._runtime = None
        self._config_sig: Optional[str] = None
        self._last_update: Dict[tuple, dict] = {}
        self._sync_semaphore: asyncio.Semaphore | None = None
        self._state_store: StateStore | None = None
        self._notifier: TelegramNotifier | None = None

    async def start(self) -> None:
        await self._rebuild_from_config(initial=True)
        self._consume_task = asyncio.create_task(self._consume_loop(), name="engine-consume")
        self._reload_task = asyncio.create_task(self._reload_loop(), name="engine-reload")

    async def stop(self) -> None:
        self._stop.set()

        for task in [self._consume_task, self._reload_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        await self._stop_watchers_and_clients()

    async def _reload_loop(self) -> None:
        while not self._stop.is_set():
            try:
                await asyncio.sleep(float(getattr(self._runtime, "min_reload_interval_sec", 1.0)))
                snap = self.cfg_mgr.snapshot()
                sig = self._make_config_signature(snap)
                if sig != self._config_sig:
                    logger.info("config changed detected, rebuilding engine")
                    await self._rebuild_from_config(initial=False)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("reload loop failed")

    async def _rebuild_from_config(self, initial: bool) -> None:
        snap = self.cfg_mgr.snapshot()
        self._runtime = snap.runtime
        self._sync_semaphore = asyncio.Semaphore(max(1, int(snap.runtime.max_concurrent_adjustments)))
        await self._ensure_state_store(snap.runtime.state_file)
        self._notifier = TelegramNotifier(
            token=snap.telegram.get("bot_token"),
            chat_id=snap.telegram.get("chat_id"),
            enabled=bool(snap.telegram.get("enabled", False)),
            cooldown_sec=int(snap.runtime.alert_cooldown_sec),
        )
        new_sig = self._make_config_signature(snap)

        if not snap.runtime.dry_run:
            logger.warning("dry_run is false: real orders may be submitted")

        # 先停旧资源
        if not initial:
            await self._stop_watchers_and_clients()

        self._clients = {}
        self._client_errors = {}
        self._watchers = []

        used_accounts = self._collect_used_accounts(snap)

        # 先建 REST clients。单个 sub 账号配置错误不应拖垮整个引擎。
        for account_name in used_accounts:
            acc = snap.accounts[account_name]
            client = None
            try:
                if acc.exchange == "gate":
                    client = GateRestClient(
                        account=acc,
                        runtime=snap.runtime,
                        base_url=acc.base_url or "https://api.gateio.ws/api/v4",
                    )
                elif acc.exchange == "websea":
                    client = WebseaRestClient(
                        account=acc,
                        runtime=snap.runtime,
                        base_url=acc.base_url or "https://oapi.websea.com",
                    )
                else:
                    raise ValueError(f"unsupported exchange: {acc.exchange}")

                await client.start()
                self._clients[account_name] = client
            except Exception as exc:
                self._client_errors[account_name] = str(exc)
                logger.exception(
                    "client init failed, account disabled for this runtime | account=%s exchange=%s",
                    account_name,
                    acc.exchange,
                )
                if client is not None:
                    try:
                        await client.close()
                    except Exception:
                        logger.exception("close failed client failed | account=%s", account_name)

        # 再建 Gate source watchers
        for unit in snap.units:
            if not unit.enabled:
                continue
            if unit.source.exchange != "gate":
                continue
            if unit.source.account not in self._clients:
                logger.error(
                    "skip source watcher because source master client is unavailable | unit=%s account=%s error=%s",
                    unit.name,
                    unit.source.account,
                    self._client_errors.get(unit.source.account, "client not found"),
                )
                continue

            src_acc = snap.accounts[unit.source.account]
            symbols = [rule.source_symbol for rule in unit.symbols if rule.enabled]
            if not symbols:
                continue

            watcher = GatePositionsWatcher(
                name=unit.name,
                ws_url=src_acc.ws_url or f"wss://fx-ws.gateio.ws/v4/ws/{unit.source.settle}",
                api_key=src_acc.api_key,
                api_secret=src_acc.api_secret,
                user_id=src_acc.user_id or "",
                settle=unit.source.settle,
                symbols=symbols,
                runtime=snap.runtime,
                on_position=lambda row, unit_name=unit.name: self._on_source_position(unit_name, row),
            )
            try:
                await watcher.start()
                self._watchers.append(watcher)
            except Exception:
                logger.exception(
                    "source watcher start failed | unit=%s account=%s",
                    unit.name,
                    unit.source.account,
                )

        self._config_sig = new_sig
        logger.info("engine rebuilt | clients=%s watchers=%s", len(self._clients), len(self._watchers))

    async def _ensure_state_store(self, state_file: str) -> None:
        path = Path(state_file)
        if self._state_store is None or self._state_store.path != path:
            self._state_store = StateStore(str(path))
            await self._state_store.load()

    async def _stop_watchers_and_clients(self) -> None:
        for watcher in self._watchers:
            try:
                await watcher.stop()
            except Exception:
                logger.exception("stop watcher failed")

        for account_name, client in self._clients.items():
            try:
                await client.close()
            except Exception:
                logger.exception("close client failed | %s", account_name)

        self._watchers = []
        self._clients = {}

    def _make_config_signature(self, snap: AppConfig) -> str:
        raw = repr(snap.runtime) + repr(snap.accounts) + repr(snap.units)
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    def _collect_used_accounts(self, snap: AppConfig) -> List[str]:
        used = set()

        for unit in snap.units:
            if not unit.enabled:
                continue

            used.add(unit.source.account)
            used.add(unit.hedge.account)

            for m in unit.source.followers:
                if m.enabled:
                    used.add(m.account)

            for m in unit.hedge.followers:
                if m.enabled:
                    used.add(m.account)

        return sorted(used)

    async def _on_source_position(self, unit_name: str, row: dict) -> None:
        if "contract" in row:
            symbol = row["contract"]
        elif "symbol" in row:
            symbol = row["symbol"]
        else:
            return

        if "size" in row:
            size = row["size"]
        elif "position" in row:
            size = row["position"]
        elif "amount" in row:
            size = row["amount"]
        else:
            return

        if symbol is None or size is None:
            return

        size_dec = Decimal(str(size))
        now = time.time()
        key = (unit_name, symbol)
        debounce_sec = float(getattr(self._runtime, "debounce_ms", 80)) / 1000.0

        prev = self._last_update.get(key)
        if prev:
            if prev["size"] == size_dec and (now - prev["ts"]) < debounce_sec:
                return

        update = {
            "unit_name": unit_name,
            "symbol": symbol,
            "size": size_dec,
            "ts": now,
            "raw": row,
        }
        self._last_update[key] = {"size": size_dec, "ts": now}
        await self._record_master_position(unit_name, symbol, size_dec)
        await self._queue.put(update)

    async def _consume_loop(self) -> None:
        while not self._stop.is_set():
            update: dict | None = None
            try:
                update = await self._queue.get()
                await self._sync_update(update)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception(
                    "sync failed | %s | %s | %s",
                    update.get("unit_name") if update else "",
                    update.get("symbol") if update else "",
                    exc,
                )
                await self._alert(
                    key="sync_loop_failed",
                    text=f"sync failed | update={update} | error={exc}",
                )

    async def _sync_update(self, update: dict) -> None:
        snap = self.cfg_mgr.snapshot()

        unit = self._find_unit(snap, update["unit_name"])
        if unit is None or not unit.enabled:
            return

        rule = self._find_symbol_rule(unit, update["symbol"])
        if rule is None or not rule.enabled:
            return

        source_pos = Decimal(str(update["size"]))

        logger.info(
            "source master accepted | unit=%s account=%s symbol=%s size=%s",
            unit.name,
            unit.source.account,
            rule.source_symbol,
            source_pos,
        )

        # Gate source master 已经通过 WebSocket 仓位更新确认，source followers 单独容错执行。
        source_jobs = []
        for member in unit.source.followers:
            if not member.enabled:
                continue
            target = source_pos * member.ratio
            source_jobs.append(
                {
                    "role": "source_follower",
                    "account": member.account,
                    "exchange": unit.source.exchange,
                    "symbol": rule.source_symbol,
                    "task": self._sync_member(
                        unit=unit,
                        account_name=member.account,
                        exchange=unit.source.exchange,
                        symbol=rule.source_symbol,
                        current_target=target,
                        leverage=unit.source.leverage,
                        margin_mode=unit.source.margin_mode,
                        settle=unit.source.settle,
                        min_sync_delta=rule.min_sync_delta,
                        step=rule.source_step,
                        min_qty=rule.source_min_qty,
                        max_pos=rule.max_source_pos,
                        max_adjust_qty=rule.max_adjust_qty,
                    ),
                }
            )

        source_followers_task = asyncio.create_task(
            self._sync_optional_members(
                unit=unit,
                rule=rule,
                group="source",
                jobs=source_jobs,
            ),
            name=f"sync-source-followers:{unit.name}:{rule.source_symbol}",
        )

        # hedge 主腿：只有 master 同步成功，才启动同组 Websea sub。
        hedge_master_target = source_pos * rule.ratio * unit.hedge.ratio
        if str(unit.hedge.mode).lower() == "opposite":
            hedge_master_target = -hedge_master_target

        hedge_master_ok = await self._sync_required_master(
            unit=unit,
            rule=rule,
            group="hedge",
            account_name=unit.hedge.account,
            exchange=unit.hedge.exchange,
            symbol=rule.hedge_symbol,
            task=self._sync_member(
                unit=unit,
                account_name=unit.hedge.account,
                exchange=unit.hedge.exchange,
                symbol=rule.hedge_symbol,
                current_target=hedge_master_target,
                leverage=unit.hedge.leverage,
                margin_mode=unit.hedge.margin_mode,
                settle=unit.hedge.settle,
                min_sync_delta=rule.min_sync_delta,
                step=rule.hedge_step,
                min_qty=rule.hedge_min_qty,
                max_pos=rule.max_hedge_pos,
                max_adjust_qty=rule.max_adjust_qty,
            ),
        )
        if not hedge_master_ok:
            logger.warning(
                "skip hedge followers because master failed | unit=%s master=%s symbol=%s",
                unit.name,
                unit.hedge.account,
                rule.hedge_symbol,
            )
            await source_followers_task
            return

        hedge_jobs = []
        for member in unit.hedge.followers:
            if not member.enabled:
                continue
            member_target = hedge_master_target * member.ratio
            hedge_jobs.append(
                {
                    "role": "hedge_follower",
                    "account": member.account,
                    "exchange": unit.hedge.exchange,
                    "symbol": rule.hedge_symbol,
                    "task": self._sync_member(
                        unit=unit,
                        account_name=member.account,
                        exchange=unit.hedge.exchange,
                        symbol=rule.hedge_symbol,
                        current_target=member_target,
                        leverage=unit.hedge.leverage,
                        margin_mode=unit.hedge.margin_mode,
                        settle=unit.hedge.settle,
                        min_sync_delta=rule.min_sync_delta,
                        step=rule.hedge_step,
                        min_qty=rule.hedge_min_qty,
                        max_pos=rule.max_hedge_pos,
                        max_adjust_qty=rule.max_adjust_qty,
                    ),
                }
            )

        await asyncio.gather(
            source_followers_task,
            self._sync_optional_members(
                unit=unit,
                rule=rule,
                group="hedge",
                jobs=hedge_jobs,
            ),
        )

    async def _sync_required_master(
        self,
        *,
        unit: UnitConfig,
        rule: SymbolRule,
        group: str,
        account_name: str,
        exchange: str,
        symbol: str,
        task,
    ) -> bool:
        try:
            result = await self._run_limited(task)
        except Exception as exc:
            logger.exception(
                "master sync failed | unit=%s group=%s account=%s exch=%s symbol=%s",
                unit.name,
                group,
                account_name,
                exchange,
                symbol,
            )
            await self._record_last_sync(
                account_name,
                symbol,
                {
                    "ok": False,
                    "role": f"{group}_master",
                    "unit": unit.name,
                    "exchange": exchange,
                    "reason": "master_error",
                    "error": str(exc),
                },
            )
            await self._alert(
                key=f"master_sync_failed:{unit.name}:{group}:{account_name}:{symbol}",
                text=(
                    f"master sync failed | unit={unit.name} group={group} "
                    f"account={account_name} symbol={symbol} error={exc}"
                ),
            )
            return False

        ok = bool(result.get("ok", False)) if isinstance(result, dict) else True
        if not ok:
            logger.warning(
                "master sync not ok | unit=%s group=%s account=%s exch=%s symbol=%s result=%s",
                unit.name,
                group,
                account_name,
                exchange,
                symbol,
                result,
            )
            await self._alert(
                key=f"master_sync_not_ok:{unit.name}:{group}:{account_name}:{symbol}",
                text=(
                    f"master sync not ok | unit={unit.name} group={group} "
                    f"account={account_name} symbol={symbol} result={result}"
                ),
            )
            return False
        return True

    async def _sync_optional_members(
        self,
        *,
        unit: UnitConfig,
        rule: SymbolRule,
        group: str,
        jobs: list[dict],
    ) -> None:
        if not jobs:
            return

        results = await asyncio.gather(
            *(self._run_limited(job["task"]) for job in jobs),
            return_exceptions=True,
        )
        errors = []
        for job, result in zip(jobs, results):
            if not isinstance(result, Exception):
                continue
            errors.append(result)
            logger.error(
                "sub sync ignored after master success | unit=%s group=%s role=%s account=%s exch=%s symbol=%s error=%s",
                unit.name,
                group,
                job["role"],
                job["account"],
                job["exchange"],
                job["symbol"],
                result,
                exc_info=(type(result), result, result.__traceback__),
            )
            await self._record_last_sync(
                job["account"],
                job["symbol"],
                {
                    "ok": False,
                    "role": job["role"],
                    "unit": unit.name,
                    "exchange": job["exchange"],
                    "reason": "sub_error_ignored",
                    "error": str(result),
                },
            )

        if errors:
            await self._alert(
                key=f"sub_sync_errors_ignored:{unit.name}:{group}:{rule.source_symbol}",
                text=(
                    f"sub sync errors ignored | unit={unit.name} group={group} "
                    f"symbol={rule.source_symbol} errors={len(errors)} first={errors[0]}"
                ),
            )

    async def _run_limited(self, task):
        if self._sync_semaphore is None:
            return await task
        async with self._sync_semaphore:
            return await task

    async def _sync_member(
        self,
        *,
        unit: UnitConfig,
        account_name: str,
        exchange: str,
        symbol: str,
        current_target: Decimal,
        leverage,
        margin_mode,
        settle,
        min_sync_delta: Decimal,
        step: Decimal,
        min_qty: Decimal,
        max_pos: Optional[Decimal],
        max_adjust_qty: Optional[Decimal],
    ) -> dict:
        client = self._clients.get(account_name)
        if client is None:
            reason = self._client_errors.get(account_name, "not initialized")
            raise RuntimeError(f"client not available: {account_name} | {reason}")

        target = Decimal(str(current_target))

        if max_pos is not None and abs(target) > Decimal(str(max_pos)):
            logger.warning(
                "sync blocked by max_pos | unit=%s account=%s symbol=%s target=%s limit=%s",
                unit.name,
                account_name,
                symbol,
                target,
                max_pos,
            )
            await self._alert(
                key=f"max_pos:{unit.name}:{account_name}:{symbol}",
                text=(
                    f"sync blocked by max_pos | unit={unit.name} account={account_name} "
                    f"symbol={symbol} target={target} limit={max_pos}"
                ),
            )
            await self._record_last_sync(
                account_name,
                symbol,
                {
                    "ok": False,
                    "blocked": True,
                    "reason": "max_pos",
                    "unit": unit.name,
                    "exchange": exchange,
                    "target": str(target),
                    "limit": str(max_pos),
                },
            )
            return {
                "ok": False,
                "blocked": True,
                "reason": "max_pos",
                "target": str(target),
            }

        kwargs = {}
        if exchange == "gate":
            kwargs["settle"] = settle

        current = await client.get_position(symbol, **kwargs)
        current = Decimal(str(current))
        delta = target - current

        if abs(delta) < Decimal(str(min_sync_delta)):
            logger.info(
                "sync | unit=%s account=%s exch=%s symbol=%s current=%s target=%s delta=%s sent=0 skipped=True reason=below_threshold",
                unit.name,
                account_name,
                exchange,
                symbol,
                current,
                target,
                delta,
            )
            result = {
                "ok": True,
                "skipped": True,
                "reason": "below_threshold",
                "unit": unit.name,
                "exchange": exchange,
                "current": str(current),
                "target": str(target),
                "delta": str(delta),
            }
            await self._record_last_sync(account_name, symbol, result)
            return result

        await client.ensure_margin_settings(
            symbol=symbol,
            leverage=leverage,
            margin_mode=margin_mode,
            **kwargs,
        )

        response = await client.adjust_position(
            symbol=symbol,
            delta=delta,
            current=current,
            target=target,
            leverage=leverage,
            margin_mode=margin_mode,
            min_qty=min_qty,
            step=step,
            max_adjust_qty=max_adjust_qty,
            **kwargs,
        )

        logger.info(
            "sync | unit=%s account=%s exch=%s symbol=%s current=%s target=%s delta=%s sent=%s skipped=False reason=",
            unit.name,
            account_name,
            exchange,
            symbol,
            current,
            target,
            delta,
            delta,
        )

        result = {
            "ok": True,
            "unit": unit.name,
            "exchange": exchange,
            "current": str(current),
            "target": str(target),
            "delta": str(delta),
            "response": response,
        }
        await self._record_last_sync(account_name, symbol, result)
        return result

    async def _record_master_position(self, unit_name: str, symbol: str, size: Decimal) -> None:
        if self._state_store is None:
            return
        try:
            await self._state_store.set_master_position(unit_name, symbol, str(size))
            await self._state_store.save()
        except Exception:
            logger.exception("save master position failed | unit=%s symbol=%s", unit_name, symbol)

    async def _record_last_sync(self, account_name: str, symbol: str, payload: dict) -> None:
        if self._state_store is None:
            return
        try:
            payload = {**payload, "updated_at": time.time()}
            await self._state_store.set_last_sync(account_name, symbol, payload)
            await self._state_store.save()
        except Exception:
            logger.exception("save last sync failed | account=%s symbol=%s", account_name, symbol)

    async def _alert(self, key: str, text: str) -> None:
        if self._notifier is None:
            return
        await self._notifier.send(key=key, text=text)

    @staticmethod
    def _find_unit(snap: AppConfig, unit_name: str) -> Optional[UnitConfig]:
        for unit in snap.units:
            if unit.name == unit_name:
                return unit
        return None

    @staticmethod
    def _find_symbol_rule(unit: UnitConfig, source_symbol: str) -> Optional[SymbolRule]:
        for rule in unit.symbols:
            if rule.source_symbol == source_symbol:
                return rule
        return None
