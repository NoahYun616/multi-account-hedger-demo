from __future__ import annotations

import hashlib
import json
import logging
import ssl
import time
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional

import aiohttp
import certifi

from clients.base import BaseRestClient

logger = logging.getLogger("client.websea_rest")


class WebseaRestClient(BaseRestClient):
    def __init__(
        self,
        *,
        account_name: str | None = None,
        name: str | None = None,
        token: str | None = None,
        api_key: str | None = None,
        secret_key: str | None = None,
        api_secret: str | None = None,
        account=None,
        account_cfg=None,
        config=None,
        runtime=None,
        base_url: str = "https://oapi.websea.com",
        **kwargs,
    ) -> None:
        super().__init__(runtime)

        acc = account or account_cfg or config

        self.name = account_name or name or getattr(acc, "name", None) or "websea"
        self.token = token or api_key or getattr(acc, "token", None) or getattr(acc, "api_key", None)
        self.secret_key = (
            secret_key
            or api_secret
            or getattr(acc, "secret_key", None)
            or getattr(acc, "api_secret", None)
        )
        self.base_url = (getattr(acc, "base_url", None) or base_url).rstrip("/")

        if not self.token:
            raise ValueError("WebseaRestClient 缺少 token/api_key")
        if not self.secret_key:
            raise ValueError("WebseaRestClient 缺少 secret_key/api_secret")

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

    def _nonce(self) -> str:
        return f"{int(time.time())}_{uuid.uuid4().hex[:5]}"

    def _sign(self, nonce: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Websea 官方签名：
        token + secret_key + nonce + 所有 GET/POST 参数的 k=v
        排序后直接拼接，再 sha1
        """
        params = params or {}
        tmp = [self.token, self.secret_key, nonce]
        for k, v in params.items():
            if v is None:
                continue
            tmp.append(f"{k}={v}")
        raw = "".join(sorted(str(x) for x in tmp))
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _check_response(path: str, data: Any) -> Any:
        if isinstance(data, dict) and int(data.get("errno", 0) or 0) != 0:
            raise RuntimeError(
                f"Websea API {path} failed: errno={data.get('errno')} errmsg={data.get('errmsg')}"
            )
        return data

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        form_body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        if self.session is None or self.session.closed:
            await self.start()

        params = params or {}
        form_body = form_body or {}

        sign_params: Dict[str, Any] = {}
        sign_params.update(params)
        sign_params.update(form_body)

        nonce = self._nonce()
        signature = self._sign(nonce, sign_params)

        headers = {
            "Token": self.token,
            "Nonce": nonce,
            "Signature": signature,
        }

        full_url = f"{self.base_url}{path}"

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
                        raise RuntimeError(f"Websea GET {path} failed: status={resp.status}, body={text}")
                    return json.loads(text) if text else {}

            if method.upper() == "POST":
                post_headers = {
                    **headers,
                    "Content-Type": "application/x-www-form-urlencoded",
                }
                async with self.session.post(
                    full_url,
                    params=params if params else None,
                    data=form_body if form_body else None,
                    headers=post_headers,
                    ssl=self._ssl_ctx,
                ) as resp:
                    text = await resp.text()
                    if resp.status >= 400:
                        raise RuntimeError(f"Websea POST {path} failed: status={resp.status}, body={text}")
                    return json.loads(text) if text else {}

            raise ValueError(f"unsupported method: {method}")

        return self._check_response(path, await self._retry(_do))

    @staticmethod
    def _extract_position_size(data: Any) -> Decimal:
        """
        Websea positions:
        result: [{type:1|2, amount:"10", ...}]
        type=1 -> long
        type=2 -> short

        这里返回净仓位：
        long 记正，short 记负。
        """
        if not isinstance(data, dict):
            return Decimal("0")

        rows = data.get("result") or []
        if not rows:
            return Decimal("0")

        net = Decimal("0")
        long_amt = Decimal("0")
        short_amt = Decimal("0")

        for row in rows:
            if not isinstance(row, dict):
                continue

            amount = Decimal(str(row.get("amount", "0")))
            pos_type = int(row.get("type", 1))

            if pos_type == 2:
                net -= amount
                short_amt += amount
            else:
                net += amount
                long_amt += amount

        if long_amt > 0 and short_amt > 0:
            logger.warning(
                "websea dual-side position detected | long=%s short=%s net=%s",
                long_amt,
                short_amt,
                net,
            )

        return net

    async def get_position(self, symbol: str, is_full: bool = False, **kwargs) -> Decimal:
        data = await self._request(
            "GET",
            "/v1/futures/position",
            params={
                "symbol": symbol,
                "is_full": 2,  # 固定全仓
            },
        )
        logger.info("websea raw position response | %s | %s | %s", self.name, symbol, data)
        size = self._extract_position_size(data)
        logger.info("websea position | %s | %s | %s", self.name, symbol, size)
        return size

    async def ensure_margin_settings(
        self,
        symbol: str,
        leverage=None,
        margin_mode: str | None = None,
        **kwargs,
    ):
        logger.info(
            "websea ensure margin settings | %s | symbol=%s leverage=%s margin_mode=cross(fixed)",
            self.name,
            symbol,
            leverage,
        )
        return {
            "ok": True,
            "skipped": True,
            "symbol": symbol,
            "leverage": leverage,
            "margin_mode": "cross",
        }

    async def _place_contract_order(
        self,
        *,
        symbol: str,
        contract_type: str,   # open / close
        side: str,            # BUY / SELL
        qty,
        leverage=None,
        price=None,
    ):
        qty_dec = Decimal(str(qty))
        if qty_dec <= 0:
            return {"ok": True, "skipped": True, "reason": "non_positive_qty"}

        is_full = 2  # 固定全仓

        order_type = "buy-market" if side.upper() == "BUY" else "sell-market"
        if price is not None:
            order_type = "buy-limit" if side.upper() == "BUY" else "sell-limit"

        form_body = {
            "contract_type": contract_type,
            "type": order_type,
            "symbol": symbol,
            "amount": str(qty_dec),
            "is_full": is_full,
        }

        if contract_type == "open" and leverage is not None:
            form_body["lever_rate"] = int(leverage)

        if price is not None:
            form_body["price"] = str(price)

        if getattr(self.runtime, "dry_run", False):
            payload = {**form_body, "dry_run": True}
            logger.info("websea dry_run contract order | %s | %s", self.name, payload)
            return {"ok": True, "dry_run": True, "payload": payload}

        logger.info("websea contract order | %s | %s", self.name, form_body)
        resp = await self._request(
            "POST",
            "/v1/futures/order/create",
            form_body=form_body,
        )
        logger.info("websea contract order response | %s | %s", self.name, resp)
        return resp

    async def place_order(
        self,
        symbol: str,
        side: str | None = None,
        qty: Any | None = None,
        *,
        action: str | None = None,
        leverage=None,
        margin_mode: str | None = None,
        price: Any | None = None,
        reduce_only: bool = False,
        **kwargs,
    ) -> Any:
        side = (side or action or "").upper()
        if not side:
            raise ValueError("Websea place_order 缺少 side/action")
        if qty is None:
            raise ValueError("Websea place_order 缺少 qty")

        contract_type = "close" if reduce_only else "open"
        return await self._place_contract_order(
            symbol=symbol,
            contract_type=contract_type,
            side=side,
            qty=qty,
            leverage=leverage,
            price=price,
        )

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
        **kwargs,
    ):
        current = Decimal(str(current if current is not None else "0"))
        target = Decimal(str(target if target is not None else (current + Decimal(str(delta)))))
        delta = Decimal(str(delta))

        if delta == 0:
            logger.info("websea adjust position skipped | %s | %s | delta=0", self.name, symbol)
            return {"ok": True, "skipped": True, "reason": "zero_delta"}

        def _normalize_qty(qty: Decimal) -> Decimal:
            q = abs(qty)
            if max_adjust_qty is not None:
                max_q = Decimal(str(max_adjust_qty))
                if q > max_q:
                    q = max_q
            if step is not None:
                q = self.quantize_down(q, Decimal(str(step)))
            if min_qty is not None:
                q = self.ensure_min_qty(q, Decimal(str(min_qty)))
            return q

        logger.info(
            "websea adjust position | %s | symbol=%s current=%s target=%s delta=%s leverage=%s",
            self.name,
            symbol,
            current,
            target,
            delta,
            leverage,
        )

        # 同方向内增减仓
        if current == 0 or target == 0 or (current > 0 and target > 0) or (current < 0 and target < 0):
            qty = _normalize_qty(delta)
            if qty == 0:
                return {"ok": True, "skipped": True, "reason": "below_min_qty"}

            side = "BUY" if delta > 0 else "SELL"
            contract_type = "close" if reduce_only else "open"

            # 同方向减仓 -> close
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

        # 跨 0 翻仓：两步走
        responses = []

        # 先平旧仓
        close_qty = _normalize_qty(current)
        if close_qty > 0:
            close_side = "SELL" if current > 0 else "BUY"
            responses.append(
                await self._place_contract_order(
                    symbol=symbol,
                    contract_type="close",
                    side=close_side,
                    qty=close_qty,
                    leverage=leverage,
                )
            )

        # 再开新仓
        open_qty = _normalize_qty(target)
        if open_qty > 0:
            open_side = "BUY" if target > 0 else "SELL"
            responses.append(
                await self._place_contract_order(
                    symbol=symbol,
                    contract_type="open",
                    side=open_side,
                    qty=open_qty,
                    leverage=leverage,
                )
            )

        return {
            "ok": True,
            "split": True,
            "current": str(current),
            "target": str(target),
            "responses": responses,
        }

    async def get_balance(self):
        data = await self._request("GET", "/v1/futures/wallet")
        logger.info("websea wallet | %s | %s", self.name, data)

        result = data.get("result") or []
        if isinstance(result, dict):
            result_list = [result]
        else:
            result_list = result

        if not result_list:
            return {
                "exchange": "websea",
                "account": self.name,
                "currency": "USDT",
                "balance": 0,
                "available": 0,
                "unrealized_pnl": 0,
            }

        item = next(
            (
                row for row in result_list
                if str(row.get("asset") or row.get("currency") or "").upper() == "USDT"
            ),
            result_list[0],
        )

        return {
            "exchange": "websea",
            "account": self.name,
            "currency": item.get("asset") or item.get("currency", "USDT"),
            "balance": float(item.get("balance", 0)),
            "available": float(item.get("avail", 0)),
            "unrealized_pnl": float(item.get("unPnl", item.get("un_profit", 0))),
            "hold": float(item.get("hold", 0)),
            "frozen": float(item.get("frozen", 0)),
        }


    async def get_all_positions(self):
        data = await self._request(
            "GET",
            "/v1/futures/position",
            params={
                "is_full": 2,
            },
        )

        logger.info("websea all positions | %s | %s", self.name, data)

        result_list = data.get("result", [])
        rows = []

        for item in result_list:
            amount = float(item.get("amount", 0))
            if amount == 0:
                continue
            pos_type = int(item.get("type", 1))  # 1=多, 2=空
            rows.append({
                "symbol": item.get("symbol"),
                "size": amount,
                "entry_price": item.get("open_price_avg") or item.get("open_price"),
                "liq_price": item.get("liquidation_price") or item.get("burst_price"),
                "pnl": float(item.get("un_profit", 0)),
                "side": "LONG" if pos_type == 1 else "SHORT",
            })

        return rows
