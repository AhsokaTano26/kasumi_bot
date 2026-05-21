import asyncio

import nonebot
from nonebot import get_plugin_config, on_command, require
from nonebot.adapters.qq import Bot, MessageEvent
from nonebot.adapters.qq.event import (
    C2CMessageCreateEvent,
    GroupAtMessageCreateEvent,
)
from nonebot.plugin import PluginMetadata

from .config import Config

require("nonebot_plugin_apscheduler")

from nonebot_plugin_apscheduler import scheduler

__plugin_meta__ = PluginMetadata(
    name="proactive",
    description="主动消息测试插件",
    usage="发送 /proactive 或 /主动测试 测试主动消息",
    config=Config,
)

config = get_plugin_config(Config)

# 存储后台任务引用，防止被垃圾回收
_background_tasks: set[asyncio.Task[None]] = set()  # type: ignore[type-arg]


# Feature 1: 命令触发的延迟主动消息
proactive_cmd = on_command("proactive", aliases={"主动测试"}, priority=10, block=True)


@proactive_cmd.handle()
async def handle_proactive(bot: Bot, event: MessageEvent) -> None:
    await proactive_cmd.send("收到！将在5秒后发送主动消息...")

    async def send_delayed() -> None:
        await asyncio.sleep(5)
        try:
            if isinstance(event, GroupAtMessageCreateEvent):
                await bot.send_to_group(
                    group_openid=event.group_openid,
                    message="这是延迟5秒后的主动消息！测试成功！",
                )
            elif isinstance(event, C2CMessageCreateEvent):
                await bot.send_to_c2c(
                    openid=event.author.user_openid,
                    message="这是延迟5秒后的主动消息！测试成功！",
                )
        except (OSError, RuntimeError):
            nonebot.logger.warning("延迟主动消息发送失败")

    task = asyncio.create_task(send_delayed())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


# Feature 2: 后台定时任务
@scheduler.scheduled_job("interval", minutes=30, id="proactive_scheduled")
async def scheduled_proactive() -> None:
    group_id = config.proactive_group_id
    if not group_id:
        return

    try:
        bot = nonebot.get_bot()
        await bot.send_to_group(
            group_openid=group_id,
            message="这是定时发送的主动消息！（每30分钟）",
        )
    except (OSError, RuntimeError):
        nonebot.logger.warning("定时主动消息发送失败，可能没有可用的bot实例")
