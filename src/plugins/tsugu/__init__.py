"""Tsugu BanGDream Bot 的 QQ 官方 Bot 前端。

QQ 群里 Bot 只能收到 @ 了它的消息，@ 会被解析成 MentionUser 段，导致
nonebot 的 TrieRule 完全不匹配。所以这里只注册一个 on_message，自己做分派。
"""

from __future__ import annotations

import time

import nonebot
import tsugu_api_async
from nonebot import get_plugin_config, on_message

# 这两个必须是运行时导入：NoneBot 靠运行时求值注解来做依赖注入，
# 注解写成 Any 会直接抛 `ValueError: Unknown parameter bot`。
# ruff 的 TC002 认不出 @tsugu.handle() 是运行时求值装饰器，故显式豁免。
from nonebot.adapters.qq import Bot  # noqa: TC002
from nonebot.adapters.qq.event import QQMessageEvent  # noqa: TC002
from nonebot.plugin import PluginMetadata, require

# 必须早于下面任何相对导入：`from .commands import ...` 会连锁 import 到 db，
# 而 db 依赖 orm 的 Model / get_session。缺这一步会抛
# RuntimeError: Cannot detect caller plugin（orm 在导入期调 localstore 找调用方插件）。
require("nonebot_plugin_orm")

from . import car, user
from . import constants as const
from .commands import HANDLERS, Ctx
from .config import Config
from .rule import (
    apply_shortcut,
    build_head_table,
    get_group_openid,
    match_command,
    normalize,
)

__plugin_meta__ = PluginMetadata(
    name="tsugu",
    description="Tsugu BanGDream Bot 的 QQ 官方 Bot 前端",
    usage="发送「help」查看全部指令",
    config=Config,
    supported_adapters={"~qq"},
)

config: Config = get_plugin_config(Config)

tsugu_api_async.settings.backend_url = config.tsugu_backend_url
tsugu_api_async.settings.userdata_backend_url = config.tsugu_data_backend_url
tsugu_api_async.settings.timeout = config.tsugu_timeout
tsugu_api_async.settings.max_retries = config.tsugu_retries
tsugu_api_async.settings.proxy = config.tsugu_proxy
tsugu_api_async.settings.backend_proxy = config.tsugu_backend_proxy
tsugu_api_async.settings.userdata_backend_proxy = config.tsugu_data_backend_proxy
tsugu_api_async.settings.use_easy_bg = config.tsugu_use_easy_bg
tsugu_api_async.settings.compress = config.tsugu_compress


def _collect_heads() -> list[tuple[str, str]]:
    """静态命令头 + 用户在 .env 里追加的别名。

    别名字段是 Set[str]，在 .env 里必须写成 JSON 数组
    （`TSUGU_SEARCH_CARD_ALIASES=["查卡","查卡牌"]`）——NoneBot 对复杂类型的
    环境变量一律走 json.loads，写成逗号分隔会直接抛 SettingsError。
    """
    heads = list(const.COMMAND_HEADS)
    builtin_heads = {head for head, _ in const.COMMAND_HEADS}

    aliases: list[tuple[str, str]] = []
    for field, command in const.ALIAS_FIELDS.items():
        for alias in getattr(config, field):
            if alias in builtin_heads:
                # build_head_table 遇到重复命令头是「后者胜」，用户别名会静默改写
                # 内置命令头的指向。这里至少留一条线索，否则很难排查。
                nonebot.logger.warning(
                    f"配置的别名 {alias!r} 与内置命令头重名，将覆盖它原本指向的命令"
                )
            aliases.append((alias, command))

    heads.extend(aliases)
    return heads


HEAD_TABLE = build_head_table(_collect_heads())

tsugu = on_message(priority=10, block=True)


@tsugu.handle()
async def _dispatch(bot: Bot, event: QQMessageEvent) -> None:
    # 这两个注解必须是运行时导入的：NoneBot 靠运行时求值注解来做依赖注入，
    # 写成 Any 会直接抛 ValueError: Unknown parameter bot。
    user_id = event.get_user_id()
    text = normalize(event.get_message().extract_plain_text())
    if not text:
        return

    pending = user.pending.pop(user_id, None)
    if pending is not None:
        if time.monotonic() - pending.created_at > config.tsugu_bind_timeout:
            await tsugu.finish(const.ERR_BIND_TIMEOUT)
            return
        command, head, args = "bind_reply", "绑定玩家", [text]
    else:
        # 车牌自动转发优先于任何命令
        if await car.maybe_forward(event, user_id, text):
            return

        matched = match_command(
            apply_shortcut(text), HEAD_TABLE, no_space=config.tsugu_no_space
        )
        if matched is None:
            return
        command, head, args = matched.command, matched.head, matched.args

    handler = HANDLERS.get(command)
    if handler is None:
        nonebot.logger.warning(f"命令 {command} 没有注册处理器")
        return

    ctx = Ctx(
        matcher=tsugu,
        bot=bot,
        event=event,
        user_id=user_id,
        group_openid=get_group_openid(event),
        args=args,
        head=head,
        at_user_id=user_id if config.tsugu_at else None,
        max_messages=config.tsugu_max_messages,
        pending=pending,
    )
    await handler(ctx)
