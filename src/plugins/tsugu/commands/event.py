"""查活动与查试炼。"""

from __future__ import annotations

from .. import api, user
from .. import constants as const
from . import Ctx, register

META_FLAG = "-m"


@register("search_event")
async def handle_search_event(ctx: Ctx) -> None:
    if not ctx.args:
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(
        await api.search_event(tsugu_user.displayed_server_list, " ".join(ctx.args))
    )


@register("event_stage")
async def handle_event_stage(ctx: Ctx) -> None:
    # -m 可以从任意位置出现，先摘掉再按位置解析
    meta = META_FLAG in ctx.args
    positional = [arg for arg in ctx.args if arg != META_FLAG]

    event_id: int | None = None
    if positional:
        if not positional[0].isdecimal():
            await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
            return
        event_id = int(positional[0])

    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(await api.event_stage(tsugu_user.main_server, event_id, meta=meta))
