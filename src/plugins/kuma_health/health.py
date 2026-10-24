"""主动探测 Kasumi 的 Webhook 和 QQ 身份接口，再上报 Kuma。"""

from __future__ import annotations

import asyncio
import logging
import time
from contextvars import ContextVar
from typing import TYPE_CHECKING

import httpx
from nonebot import get_adapter, logger
from nonebot.adapters.qq import Adapter, Bot
from nonebot.drivers import ASGIMixin

if TYPE_CHECKING:
    from nonebot.drivers import Driver

CHECK_INTERVAL = 60
REQUEST_TIMEOUT = 10
_pushing: ContextVar[bool] = ContextVar("kuma_health_pushing", default=False)


class _PushLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # noqa: ARG002
        # HTTPX 在 INFO 级别输出完整 URL，只屏蔽当前上报请求的日志。
        return not _pushing.get()


logging.getLogger("httpx").addFilter(_PushLogFilter())


class HealthReporter:
    """每轮主动验证状态，探测用 Bot 仅缓存鉴权令牌。"""

    def __init__(self, driver: Driver, push_url: str) -> None:
        self.driver = driver
        self.push_url = push_url
        self._bots: dict[str, Bot] = {}

    async def check(self, client: httpx.AsyncClient) -> tuple[str, str]:
        if not isinstance(self.driver, ASGIMixin):
            return "down", "Webhook application unavailable"

        adapter = get_adapter(Adapter)
        accounts = adapter.qq_config.qq_bots
        if not accounts:
            return "down", "No QQ accounts configured"

        host = str(self.driver.config.host)
        host = {"0.0.0.0": "127.0.0.1", "::": "::1"}.get(host, host)
        webhook_url = httpx.URL(
            scheme="http", host=host, port=self.driver.config.port, path="/qq/webhook"
        )
        challenge = "kuma-health"
        response = await client.post(
            webhook_url,
            headers={"X-Bot-Appid": accounts[0].id},
            json={
                "op": 13,
                "d": {"plain_token": challenge, "event_ts": str(int(time.time()))},
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        verification = response.json()
        if verification.get("plain_token") != challenge or not verification.get(
            "signature"
        ):
            return "down", "Webhook verification failed"

        bots: list[Bot] = []
        for account in accounts:
            if account.id not in self._bots:
                self._bots[account.id] = Bot(adapter, account.id, account)
            bots.append(self._bots[account.id])

        identities = await asyncio.gather(
            *(asyncio.wait_for(bot.me(), timeout=REQUEST_TIMEOUT) for bot in bots),
            return_exceptions=True,
        )
        for identity in identities:
            if isinstance(identity, BaseException):
                return "down", f"QQ identity check failed ({type(identity).__name__})"
            if not identity.id.strip():
                return "down", "QQ identity unavailable"
        return "up", "Webhook and QQ identity OK"

    async def report_once(self, client: httpx.AsyncClient) -> None:
        started = time.monotonic()
        try:
            status, message = await self.check(client)
        except Exception as error:  # noqa: BLE001 任何探测异常都必须上报 down
            status, message = "down", f"Health check failed ({type(error).__name__})"

        try:
            url = httpx.URL(self.push_url).copy_merge_params(
                {
                    "status": status,
                    "msg": message,
                    "ping": f"{(time.monotonic() - started) * 1000:.2f}"
                    if status == "up"
                    else "",
                }
            )
            token = _pushing.set(True)
            try:
                response = await client.get(url, timeout=REQUEST_TIMEOUT)
            finally:
                _pushing.reset(token)
            response.raise_for_status()
            if response.json().get("ok") is not True:
                logger.warning("kuma_health: Kuma rejected the push")
        except Exception as error:  # noqa: BLE001 上报失败不终止后台任务
            # 异常文本可能含 Push URL 的令牌，只记录异常类型。
            logger.warning(f"kuma_health: Push failed ({type(error).__name__})")

    async def run(self) -> None:
        # 等监听端口与适配器就绪；本机探测不经过环境代理。
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT, trust_env=False
        ) as client:
            await asyncio.sleep(CHECK_INTERVAL)
            while True:
                started = time.monotonic()
                await self.report_once(client)
                await asyncio.sleep(
                    max(0, CHECK_INTERVAL - (time.monotonic() - started))
                )
