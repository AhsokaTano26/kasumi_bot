"""Kasumi 的 Uptime Kuma 健康上报插件。"""

from __future__ import annotations

import asyncio
from contextlib import suppress

from nonebot import get_driver, get_plugin_config, logger
from nonebot.plugin import PluginMetadata

from .config import Config
from .health import HealthReporter

__plugin_meta__ = PluginMetadata(
    name="kuma_health",
    description="每 60 秒检查 Webhook 与 QQ 身份接口并上报 Uptime Kuma",
    usage="配置环境变量 KUMA_PUSH_URL 后重启应用",
    config=Config,
    supported_adapters={"~qq"},
)

config: Config = get_plugin_config(Config)
driver = get_driver()
_task: asyncio.Task[None] | None = None


@driver.on_startup
async def start() -> None:
    global _task  # noqa: PLW0603 生命周期共用一个任务句柄
    push_url = config.kuma_push_url.strip()
    if not push_url or (_task is not None and not _task.done()):
        return
    reporter = HealthReporter(driver, push_url)
    _task = asyncio.create_task(reporter.run(), name="kuma_health")
    logger.info("kuma_health: Health reporting enabled (60 seconds)")


@driver.on_shutdown
async def stop() -> None:
    global _task  # noqa: PLW0603 生命周期共用一个任务句柄
    if _task is not None:
        _task.cancel()
        with suppress(asyncio.CancelledError):
            await _task
        _task = None
