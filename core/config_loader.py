from __future__ import annotations

import asyncio
import copy
import json
import logging
from decimal import Decimal
from pathlib import Path
from typing import Any

from core.models import (
    AccountConfig,
    AppConfig,
    Leg,
    Member,
    RuntimeConfig,
    SymbolRule,
    UnitConfig,
)

logger = logging.getLogger("config")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing config file: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _to_decimal(value: Any, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class ConfigManager:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._app_config: AppConfig | None = None
        self._mtimes: dict[Path, float] = {}
        self._task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    @property
    def global_path(self) -> Path:
        return self.config_dir / "global_config.json"

    @property
    def strategy_path(self) -> Path:
        return self.config_dir / "strategy_config.json"

    @property
    def accounts_path(self) -> Path:
        return self.config_dir / "accounts.json"

    async def start(self) -> None:
        await self.reload(force=True)
        self._task = asyncio.create_task(self._watch_loop(), name="config-watch")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _watch_loop(self) -> None:
        while True:
            await asyncio.sleep(self.runtime().min_reload_interval_sec)
            await self.reload(force=False)

    def runtime(self) -> RuntimeConfig:
        if self._app_config is None:
            raise RuntimeError("config not loaded")
        return self._app_config.runtime

    def snapshot(self) -> AppConfig:
        if self._app_config is None:
            raise RuntimeError("config not loaded")
        return copy.deepcopy(self._app_config)

    async def reload(self, force: bool = False) -> bool:
        async with self._lock:
            changed = force
            for path in (self.global_path, self.strategy_path, self.accounts_path):
                if not path.exists():
                    raise FileNotFoundError(f"missing config file: {path}")
                mtime = path.stat().st_mtime
                if self._mtimes.get(path) != mtime:
                    changed = True

            if not changed:
                return False

            global_cfg = _read_json(self.global_path)
            strategy_cfg = _read_json(self.strategy_path)
            accounts_cfg = _read_json(self.accounts_path)

            self._app_config = self._build(global_cfg, strategy_cfg, accounts_cfg)
            self._mtimes = {
                self.global_path: self.global_path.stat().st_mtime,
                self.strategy_path: self.strategy_path.stat().st_mtime,
                self.accounts_path: self.accounts_path.stat().st_mtime,
            }
            logger.info("config reloaded | units=%s", len(self._app_config.units))
            return True

    def _build(
        self,
        global_cfg: dict[str, Any],
        strategy_cfg: dict[str, Any],
        accounts_cfg: dict[str, Any],
    ) -> AppConfig:
        runtime = RuntimeConfig(
            poll_interval_sec=float(global_cfg.get("poll_interval_sec", 1.0)),
            debounce_ms=int(global_cfg.get("debounce_ms", 80)),
            http_timeout=float(global_cfg.get("http_timeout", 10)),
            ws_ping_interval=float(global_cfg.get("ws_ping_interval", 10)),
            ws_ping_timeout=float(global_cfg.get("ws_ping_timeout", 10)),
            reconnect_delay_sec=float(global_cfg.get("reconnect_delay_sec", 3)),
            state_file=str(global_cfg.get("state_file", "logs/state.json")),
            alert_cooldown_sec=int(global_cfg.get("alert_cooldown_sec", 60)),
            sync_timeout_warn_sec=float(global_cfg.get("sync_timeout_warn_sec", 3)),
            max_position_deviation=_to_decimal(global_cfg.get("max_position_deviation", "0")),
            dry_run=_normalize_bool(global_cfg.get("dry_run", True), True),
            log_level=str(global_cfg.get("log_level", "INFO")),
            max_concurrent_adjustments=int(global_cfg.get("max_concurrent_adjustments", 20)),
            min_reload_interval_sec=float(global_cfg.get("min_reload_interval_sec", 1)),
            order_retry_times=int(global_cfg.get("order_retry_times", 3)),
            order_retry_delay_sec=float(global_cfg.get("order_retry_delay_sec", 0.5)),
        )

        raw_accounts = accounts_cfg.get("accounts", {})
        if not isinstance(raw_accounts, dict) or not raw_accounts:
            raise ValueError("accounts.json 中 accounts 不能为空且必须为对象")

        accounts: dict[str, AccountConfig] = {}
        for name, item in raw_accounts.items():
            accounts[name] = AccountConfig(
                name=name,
                exchange=str(item["exchange"]),
                api_key=item.get("api_key"),
                api_secret=item.get("api_secret"),
                token=item.get("token"),
                secret_key=item.get("secret_key"),
                user_id=item.get("user_id"),
                base_url=item.get("base_url"),
                ws_url=item.get("ws_url"),
            )

        telegram = accounts_cfg.get("telegram", {})
        raw_units = strategy_cfg.get("units", [])
        if not isinstance(raw_units, list) or not raw_units:
            raise ValueError("strategy_config.json 中 units 不能为空且必须为数组")

        units: list[UnitConfig] = []
        for item in raw_units:
            source_followers = [
                Member(
                    account=str(x["account"]),
                    ratio=_to_decimal(x.get("ratio", "1"), "1"),
                    enabled=_normalize_bool(x.get("enabled", True), True),
                )
                for x in item["source"].get("followers", [])
            ]

            hedge_followers = [
                Member(
                    account=str(x["account"]),
                    ratio=_to_decimal(x.get("ratio", "1"), "1"),
                    enabled=_normalize_bool(x.get("enabled", True), True),
                )
                for x in item["hedge"].get("followers", [])
            ]

            source = Leg(
                account=str(item["source"]["account"]),
                exchange=str(item["source"]["exchange"]),
                leverage=int(item["source"]["leverage"]) if item["source"].get("leverage") is not None else None,
                margin_mode=item["source"].get("margin_mode"),
                settle=str(item["source"].get("settle", "usdt")),
                mode=str(item["source"].get("mode", "same")),
                ratio=_to_decimal(item["source"].get("ratio", "1"), "1"),
                followers=source_followers,
            )

            hedge = Leg(
                account=str(item["hedge"]["account"]),
                exchange=str(item["hedge"]["exchange"]),
                leverage=int(item["hedge"]["leverage"]) if item["hedge"].get("leverage") is not None else None,
                margin_mode=item["hedge"].get("margin_mode"),
                settle=str(item["hedge"].get("settle", "usdt")),
                mode=str(item["hedge"].get("mode", "same")),
                ratio=_to_decimal(item["hedge"].get("ratio", "1"), "1"),
                followers=hedge_followers,
            )

            symbols = [
                SymbolRule(
                    source_symbol=str(x["source_symbol"]),
                    hedge_symbol=str(x["hedge_symbol"]),
                    enabled=_normalize_bool(x.get("enabled", True), True),
                    ratio=_to_decimal(x.get("ratio", "1"), "1"),
                    min_sync_delta=_to_decimal(x.get("min_sync_delta", "0")),
                    source_step=_to_decimal(x.get("source_step", "1"), "1"),
                    hedge_step=_to_decimal(x.get("hedge_step", "1"), "1"),
                    source_min_qty=_to_decimal(x.get("source_min_qty", "1"), "1"),
                    hedge_min_qty=_to_decimal(x.get("hedge_min_qty", "1"), "1"),
                    max_source_pos=_to_decimal(x["max_source_pos"]) if x.get("max_source_pos") is not None else None,
                    max_hedge_pos=_to_decimal(x["max_hedge_pos"]) if x.get("max_hedge_pos") is not None else None,
                    max_adjust_qty=_to_decimal(x["max_adjust_qty"]) if x.get("max_adjust_qty") is not None else None,
                )
                for x in item.get("symbols", [])
            ]

            if not symbols:
                raise ValueError(f"策略单元 {item.get('name')} 没有 symbols 配置")

            for acc_name in [source.account, hedge.account]:
                if acc_name not in accounts:
                    raise ValueError(f"策略单元 {item.get('name')} 引用了不存在的账号: {acc_name}")

            for m in source.followers + hedge.followers:
                if m.account not in accounts:
                    raise ValueError(f"策略单元 {item.get('name')} follower 引用了不存在的账号: {m.account}")

            units.append(
                UnitConfig(
                    name=str(item["name"]),
                    enabled=_normalize_bool(item.get("enabled", True), True),
                    source=source,
                    hedge=hedge,
                    symbols=symbols,
                )
            )

        return AppConfig(
            runtime=runtime,
            accounts=accounts,
            units=units,
            telegram=telegram,
        )


def load_app_config(config_dir: str = "config") -> AppConfig:
    """
    兼容辅助函数：给新版调用方式留个入口。
    """
    mgr = ConfigManager(config_dir=config_dir)
    global_cfg = _read_json(mgr.global_path)
    strategy_cfg = _read_json(mgr.strategy_path)
    accounts_cfg = _read_json(mgr.accounts_path)
    return mgr._build(global_cfg, strategy_cfg, accounts_cfg)