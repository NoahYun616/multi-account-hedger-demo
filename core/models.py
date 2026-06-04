from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class RuntimeConfig:
    poll_interval_sec: float = 1.0
    debounce_ms: int = 80
    http_timeout: float = 10.0
    ws_ping_interval: float = 10.0
    ws_ping_timeout: float = 10.0
    reconnect_delay_sec: float = 3.0
    state_file: str = "logs/state.json"
    alert_cooldown_sec: int = 60
    sync_timeout_warn_sec: float = 3.0
    max_position_deviation: Decimal = Decimal("0")
    dry_run: bool = True
    log_level: str = "INFO"
    max_concurrent_adjustments: int = 20
    min_reload_interval_sec: float = 1.0
    order_retry_times: int = 3
    order_retry_delay_sec: float = 0.5


@dataclass
class AccountConfig:
    name: str
    exchange: str
    api_key: str | None = None
    api_secret: str | None = None
    token: str | None = None
    secret_key: str | None = None
    user_id: str | None = None
    base_url: str | None = None
    ws_url: str | None = None


@dataclass
class Member:
    account: str
    ratio: Decimal = Decimal("1")
    enabled: bool = True


@dataclass
class Leg:
    account: str
    exchange: str
    leverage: int | None = None
    margin_mode: str | None = None
    settle: str = "usdt"
    mode: str = "same"
    ratio: Decimal = Decimal("1")
    followers: list[Member] = field(default_factory=list)


@dataclass
class SymbolRule:
    source_symbol: str
    hedge_symbol: str
    enabled: bool = True
    ratio: Decimal = Decimal("1")
    min_sync_delta: Decimal = Decimal("0")
    source_step: Decimal = Decimal("1")
    hedge_step: Decimal = Decimal("1")
    source_min_qty: Decimal = Decimal("1")
    hedge_min_qty: Decimal = Decimal("1")
    max_source_pos: Decimal | None = None
    max_hedge_pos: Decimal | None = None
    max_adjust_qty: Decimal | None = None


@dataclass
class UnitConfig:
    name: str
    enabled: bool
    source: Leg
    hedge: Leg
    symbols: list[SymbolRule]

    def find_symbol_by_source(self, source_symbol: str) -> SymbolRule | None:
        for item in self.symbols:
            if item.enabled and item.source_symbol == source_symbol:
                return item
        return None


@dataclass
class AppConfig:
    runtime: RuntimeConfig
    accounts: dict[str, AccountConfig]
    units: list[UnitConfig]
    telegram: dict[str, Any] = field(default_factory=dict)


@dataclass
class PositionUpdate:
    unit_name: str
    source_symbol: str
    master_size: Decimal
    raw_payload: dict[str, Any]


@dataclass
class SyncResult:
    account: str
    exchange: str
    symbol: str
    current: Decimal
    target: Decimal
    delta: Decimal
    sent: Decimal
    skipped: bool = False
    reason: str = ""
