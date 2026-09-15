"""预测线：ycx / ycxall / lsycx。

三个命令的参数都是「[档位] [活动ID] [服务器]」，但活动 ID 与服务器都可省略。
解析方式是先把开头的纯数字当活动 ID 摘掉，剩下的第一个非数字当服务器，
这样 `ycx 1000`、`ycx 1000 177`、`ycx 1000 jp`、`ycx 1000 177 jp` 都能正确解析。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .. import api, user
from .. import constants as const
from . import Ctx, register

if TYPE_CHECKING:
    from tsugu_api_core._typing import ServerId


async def _resolve_event_and_server(
    ctx: Ctx, rest: list[str]
) -> tuple[int | None, ServerId | None] | None:
    """从剩余参数里解析出 (活动ID, 服务器ID)。解析失败时已回复错误并返回 None。"""
    rest = list(rest)

    event_id: int | None = None
    if rest and rest[0].isdecimal():
        event_id = int(rest.pop(0))

    server: ServerId | None = None
    if rest:
        try:
            server = await api.resolve_server(rest[0])
        except ValueError as exc:
            await ctx.reply_error(str(exc))
            return None

    return event_id, server


@register("cutoff")
async def handle_cutoff(ctx: Ctx) -> None:
    if not ctx.args or not ctx.args[0].isdecimal():
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    tier = int(ctx.args[0])
    parsed = await _resolve_event_and_server(ctx, ctx.args[1:])
    if parsed is None:
        return
    event_id, server = parsed

    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(
        await api.cutoff_detail(server or tsugu_user.main_server, tier, event_id)
    )


@register("cutoff_all")
async def handle_cutoff_all(ctx: Ctx) -> None:
    parsed = await _resolve_event_and_server(ctx, ctx.args)
    if parsed is None:
        return
    event_id, server = parsed

    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(await api.cutoff_all(server or tsugu_user.main_server, event_id))


@register("cutoff_history")
async def handle_cutoff_history(ctx: Ctx) -> None:
    if not ctx.args or not ctx.args[0].isdecimal():
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    tier = int(ctx.args[0])
    parsed = await _resolve_event_and_server(ctx, ctx.args[1:])
    if parsed is None:
        return
    event_id, server = parsed

    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(
        await api.cutoff_history(server or tsugu_user.main_server, tier, event_id)
    )
