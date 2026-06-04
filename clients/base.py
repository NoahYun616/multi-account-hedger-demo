from __future__ import annotations

import asyncio
import logging
from decimal import Decimal, ROUND_DOWN
from typing import Any, Awaitable, Callable


logger = logging.getLogger("client.base")


class _BaseClient:
    """
    统一基础能力：
    - runtime 挂载
    - 重试
    - 数量步进裁剪
    """

    def __init__(self, runtime: Any) -> None:
        self.runtime = runtime

    async def _retry(
        self,
        func: Callable[..., Awaitable[Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        retries = int(getattr(self.runtime, "order_retry_times", 3))
        delay = float(getattr(self.runtime, "order_retry_delay_sec", 0.5))

        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                return await func(*args, **kwargs)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                last_error = exc
                if attempt >= retries:
                    break

                sleep_s = delay * attempt
                logger.warning(
                    "request retry | attempt=%s/%s | sleep=%.2fs | error=%s",
                    attempt,
                    retries,
                    sleep_s,
                    exc,
                )
                await asyncio.sleep(sleep_s)

        assert last_error is not None
        raise last_error

    @staticmethod
    def quantize_down(value: Decimal, step: Decimal) -> Decimal:
        if step <= 0:
            return value
        return (value / step).to_integral_value(rounding=ROUND_DOWN) * step

    @staticmethod
    def ensure_min_qty(value: Decimal, min_qty: Decimal) -> Decimal:
        if value == 0:
            return value
        if abs(value) < min_qty:
            return Decimal("0")
        return value

    async def close(self) -> None:
        return None


class BaseRestClient(_BaseClient):
    pass


class BaseExchangeClient(_BaseClient):
    pass