from __future__ import annotations

import hashlib
import hmac
import json
import logging
import ssl
import time
from decimal import Decimal
from typing import Any, Optional
from urllib.parse import urlencode, urlparse

import aiohttp
import certifi

from clients.base import BaseExchangeClient

logger = logging.getLogger("client.gate_rest")


class GateRestClient(BaseExchangeClient):
    def __init__(
        self,
        *,
        account_name: str | None = None,
        name: str | None = None,
        api_key: str | None = None,
        key: str | None = None,
        api_secret: str | None = None,
        secret: str | None = None,
        account=None,
        account_cfg=None,
        config=None,
        runtime=None,
        base_url: str = "https://api.gateio.ws/api/v4",
        settle: str = "usdt",
        **kwargs,
    ) -> None:
        super().__init__(runtime)

        acc = account or account_cfg or config

        self.name = (
            account_name
            or name
            or getattr(acc, "name", None)
            or "gate"
        )

        self.api_key = (
            api_key
            or key
            or getattr(acc, "api_key", None)
            or getattr(acc, "key", None)
        )

        self.api_secret = (
            api_secret
            or secret
            or getattr(acc, "api_secret", None)
            or getattr(acc, "secret", None)
        )

        self.base_url = (
            kwargs.get("base_url")
            or getattr(acc, "base_url", None)
            or base_url
        ).rstrip("/")

        self.settle = (
            kwargs.get("settle")
            or getattr(acc, "settle", None)
            or settle
        )

        if not self.api_key:
            raise ValueError(f"GateRestClient 缺少 api_key/key | account={self.name}")
        if not self.api_secret:
            raise ValueError(f"GateRestClient 缺少 api_secret/secret | account={self.name}")

        self._ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        self._connector = None
        self.session = None

    async def start(self) -> None:
        if self.session is not None and not self.session.closed:
            return
        self._connector = aiohttp.TCPConnector(ssl=self._ssl_ctx)
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=float(getattr(self.runtime, "http_timeout", 10))),
            connector=self._connector,
        )

    async def close(self) -> None:
        if self.session is not None and not self.session.closed:
            await self.session.close()
        self.session = None
        self._connector = None

    def _sign_headers(
        self,
        method: str,
        full_url: str,
        query_string: str = "",
        body_text: str = "",
    ) -> dict[str, str]:
        ts = str(int(time.time()))
        parsed = urlparse(full_url)
        path = parsed.path

        body_hash = hashlib.sha512(body_text.encode("utf-8")).hexdigest()
        sign_string = "\n".join([
            method.upper(),
            path,
            query_string,
            body_hash,
            ts,
        ])
        sign = hmac.new(
            self.api_secret.encode("utf-8"),
            sign_string.encode("utf-8"),
            hashlib.sha512,
        ).hexdigest()

        return {
            "KEY": self.api_key,
            "Timestamp": ts,
            "SIGN": sign,
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json_body: Optional[dict[str, Any]] = None,
    ) -> Any:
        if self.session is None or self.session.closed:
            await self.start()

        params = params or {}
        json_body = json_body or {}

        full_url = f"{self.base_url}{path}"
        query_string = urlencode(sorted((k, str(v)) for k, v in params.items()))
        body_text = json.dumps(json_body, separators=(",", ":"), ensure_ascii=False) if json_body else ""
        headers = self._sign_headers(method, full_url, query_string, body_text)

        async def _do():
            if method.upper() == "GET":
                async with self.session.get(
                    full_url,
                    params=params,
                    headers=headers,
                    ssl=self._ssl_ctx,
                ) as resp:
                    text = await resp.text()
                    if resp.status >= 400:
                        raise RuntimeError(f"Gate GET {path} failed: status={resp.status}, body={text}")
                    return json.loads(text) if text else {}

            if method.upper() == "POST":
                async with self.session.post(
                    full_url,
                    params=params if params else None,
                    data=body_text if body_text else None,
                    headers=headers,
                    ssl=self._ssl_ctx,
                ) as resp:
                    text = await resp.text()
                    if resp.status >= 400:
                        raise RuntimeError(f"Gate POST {path} failed: status={resp.status}, body={text}")
                    return json.loads(text) if text else {}

            raise ValueError("unsupported method: %s" % method)

        return await self._retry(_do)

    async def get_position(self, symbol: str, settle: str | None = None, **kwargs) -> Decimal:
        settle = settle or self.settle
        data = await self._request(
            "GET",
            "/futures/{}/positions/{}".format(settle, symbol),
        )

        logger.info("gate raw position response | %s | %s | %s", self.name, symbol, data)

        size = Decimal("0")
        if isinstance(data, dict):
            size = Decimal(str(data.get("size", "0")))

        logger.info("gate position | %s | %s | %s", self.name, symbol, size)
        return size

    async def ensure_margin_settings(
        self,
        symbol: str,
        leverage=None,
        margin_mode: str | None = None,
        **kwargs,
    ):
        """
        当前先做兼容 no-op。
        后续如果你要强制设置 Gate 的 leverage / margin_mode，
        再把这里接成真实接口。
        """
        logger.info(
            "gate ensure margin settings | %s | symbol=%s leverage=%s margin_mode=%s",
            self.name,
            symbol,
            leverage,
            margin_mode,
        )
        return {
            "ok": True,
            "skipped": True,
            "symbol": symbol,
            "leverage": leverage,
            "margin_mode": margin_mode,
        }

    async def place_order(
        self,
        symbol: str,
        side: str | None = None,
        qty: Any | None = None,
        *,
        action: str | None = None,
        size: Any | None = None,
        settle: str | None = None,
        price: Any | None = None,
        tif: str = "ioc",
        reduce_only: bool = False,
        **kwargs,
    ) -> Any:
        settle = settle or self.settle
        order_side = (side or action or "").upper()
        order_qty = qty if qty is not None else size

        if not order_side:
            raise ValueError("Gate place_order 缺少 side/action")
        if order_qty is None:
            raise ValueError("Gate place_order 缺少 qty/size")

        signed_size = Decimal(str(order_qty))
        if order_side == "SELL":
            signed_size = -abs(signed_size)
        else:
            signed_size = abs(signed_size)

        payload = {
            "contract": symbol,
            "size": str(signed_size),
            "reduce_only": bool(reduce_only),
            "tif": tif,
        }

        # Gate futures 常见做法：price=0 + ioc 近似市价执行
        if price is not None:
            payload["price"] = str(price)
        else:
            payload["price"] = "0"

        if getattr(self.runtime, "dry_run", False):
            payload["dry_run"] = True
            logger.info("gate dry_run order | %s | %s", self.name, payload)
            return {"ok": True, "dry_run": True, "payload": payload}

        logger.info("gate place order | %s | %s", self.name, payload)
        resp = await self._request(
            "POST",
            "/futures/{}/orders".format(settle),
            json_body=payload,
        )
        logger.info("gate place order response | %s | %s", self.name, resp)
        return resp

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
        margin_mode: str | None = None,
        settle: str | None = None,
        **kwargs,
    ):
        """
        Gate 这里按净仓位调仓：
        - delta > 0 -> BUY
        - delta < 0 -> SELL

        因为 Gate futures 这边通常是净持仓模型，
        所以不需要像 Websea 那样强制拆成 close/open 两步。
        """
        settle = settle or self.settle
        delta = Decimal(str(delta))

        if delta == 0:
            logger.info("gate adjust position skipped | %s | %s | delta=0", self.name, symbol)
            return {"ok": True, "skipped": True, "reason": "zero_delta"}

        qty = abs(delta)

        if max_adjust_qty is not None:
            max_adjust_qty = Decimal(str(max_adjust_qty))
            if qty > max_adjust_qty:
                qty = max_adjust_qty

        if step is not None:
            qty = self.quantize_down(qty, Decimal(str(step)))

        if min_qty is not None:
            qty = self.ensure_min_qty(qty, Decimal(str(min_qty)))

        if qty == 0:
            logger.info(
                "gate adjust position skipped | %s | %s | delta=%s | qty=0 after quantize/min_qty",
                self.name,
                symbol,
                delta,
            )
            return {"ok": True, "skipped": True, "reason": "below_min_qty"}

        side = "BUY" if delta > 0 else "SELL"

        logger.info(
            "gate adjust position | %s | symbol=%s current=%s target=%s delta=%s qty=%s side=%s leverage=%s",
            self.name,
            symbol,
            current,
            target,
            delta,
            qty,
            side,
            leverage,
        )

        return await self.place_order(
            symbol=symbol,
            side=side,
            qty=str(qty),
            settle=settle,
            reduce_only=reduce_only,
            **kwargs,
        )
    async def get_balance(self, settle: str | None = None):
        settle = settle or self.settle

        data = await self._request(
            "GET",
            f"/futures/{settle}/accounts",
        )

        logger.info("gate balance | %s | %s", self.name, data)

        return {
            "exchange": "gate",
            "account": self.name,
            "currency": settle.upper(),
            "balance": data.get("total"),
            "available": data.get("available"),
            "unrealized_pnl": data.get("unrealised_pnl"),
        }

    async def get_all_positions(self, settle: str | None = None):
        settle = settle or self.settle

        data = await self._request(
            "GET",
            f"/futures/{settle}/positions",
        )

        rows = []

        if isinstance(data, list):
            for item in data:
                size = Decimal(str(item.get("size", "0")))
                if size == 0:
                    continue

                rows.append({
                    "symbol": item.get("contract"),
                    "size": str(size),
                    "entry_price": item.get("entry_price"),
                    "liq_price": item.get("liq_price"),
                    "pnl": item.get("unrealised_pnl"),
                    "side": "LONG" if size > 0 else "SHORT",
                })

        logger.info("gate all positions | %s | %s", self.name, rows)
        return rows