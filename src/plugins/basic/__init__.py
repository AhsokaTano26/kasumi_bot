from nonebot import get_plugin_config, on_command
from nonebot.adapters.qq import MessageEvent
from nonebot.adapters.qq.event import (
    C2CMessageCreateEvent,
    GroupAtMessageCreateEvent,
)
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="basic",
    description="基础命令插件",
    usage="发送 /help 等命令",
    config=Config,
)

config = get_plugin_config(Config)


# 帮助命令
help_cmd = on_command("help", aliases={"帮助"}, priority=10, block=True)

HELP_TEXT = """可用命令列表：

基础命令：
/help 显示此帮助信息

BanG Dream：
/bangdream 角色知识问答

演出查询：
/live 或 /未来演出 - 查询近期演出信息
/live <乐队名> - 按乐队筛选演出
/刷新演出 - 手动刷新演出数据
"""


@help_cmd.handle()
async def handle_help() -> None:
    await help_cmd.finish(HELP_TEXT)


# ID 查询命令
id_cmd = on_command("id", aliases={"getid", "查询id"}, priority=10, block=True)


@id_cmd.handle()
async def handle_id(event: MessageEvent) -> None:
    user_id = event.get_user_id()
    lines = [f"UserID: {user_id}"]

    if isinstance(event, GroupAtMessageCreateEvent):
        lines.append(f"GroupID: {event.group_openid}")
    elif isinstance(event, C2CMessageCreateEvent):
        lines.append("类型: 私聊（无GroupID）")

    await id_cmd.finish("\n".join(lines))
