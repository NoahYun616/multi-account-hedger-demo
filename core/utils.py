from __future__ import annotations

import json
import logging
import logging.handlers
import os
from decimal import Decimal, ROUND_DOWN, ROUND_UP
from pathlib import Path
from typing import Any


_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def setup_logging(level: str | None = None, log_file: str = "logs/system.log") -> None:
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    if root.handlers:
        return

    resolved = getattr(logging, (level or os.getenv("LOG_LEVEL") or "INFO").upper(), logging.INFO)
    root.setLevel(resolved)

    formatter = logging.Formatter(_LOG_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    rotating = logging.handlers.RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=10, encoding="utf-8")
    rotating.setFormatter(formatter)
    root.addHandler(rotating)


def load_json(path: str | Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def to_decimal(value: Any, default: Decimal = Decimal("0")) -> Decimal:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return default


def quantize_to_step(value: Decimal, step: Decimal, rounding=ROUND_DOWN) -> Decimal:
    if step <= 0:
        return value
    units = (value / step).to_integral_value(rounding=rounding)
    return units * step


def signed_side(delta: Decimal) -> str:
    return "buy" if delta > 0 else "sell"


def normalize_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def round_towards_zero(value: Decimal, step: Decimal) -> Decimal:
    rounding = ROUND_DOWN if value >= 0 else ROUND_UP
    return quantize_to_step(value, step, rounding=rounding)
