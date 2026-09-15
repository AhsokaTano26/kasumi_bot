"""查卡池、抽卡模拟与群级抽卡开关。"""

from __future__ import annotations

from .. import api, db, user
from .. import constants as const
from . import Ctx, register


@register("search_gacha")
async def handle_search_gacha(ctx: Ctx) -> None:
    if not ctx.args:
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    if not ctx.args[0].removeprefix("-").isdecimal():
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(
        await api.search_gacha(tsugu_user.displayed_server_list, int(ctx.args[0]))
    )


@register("gacha_simulate")
async def handle_gacha_simulate(ctx: Ctx) -> None:
    if not ctx.args or not ctx.args[0].isdecimal():
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    if ctx.group_openid is not None and not await db.is_gacha_enabled(ctx.group_openid):
        await ctx.reply_text(const.ERR_GACHA_DISABLED)
        return

    times = int(ctx.args[0])
    has_gacha_id = len(ctx.args) > 1 and ctx.args[1].isdecimal()
    gacha_id = int(ctx.args[1]) if has_gacha_id else None

    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(await api.gacha_simulate(tsugu_user.main_server, times, gacha_id))


async def _switch_gacha(ctx: Ctx, *, enabled: bool) -> None:
    if ctx.group_openid is None:
        await ctx.reply_text(const.ERR_GROUP_ONLY)
        return
    await db.set_gacha_enabled(ctx.group_openid, enabled=enabled)
    await ctx.reply_text("开启成功" if enabled else "关闭成功")


@register("gacha_switch")
async def handle_gacha_switch(ctx: Ctx) -> None:
    if not ctx.args:
        await ctx.reply_text("无效指令")
        return
    word = ctx.args[0]
    if word in ("on", "开启"):
        await _switch_gacha(ctx, enabled=True)
    elif word in ("off", "关闭"):
        await _switch_gacha(ctx, enabled=False)
    else:
        await ctx.reply_text("无效指令")


@register("gacha_on")
async def handle_gacha_on(ctx: Ctx) -> None:
    await _switch_gacha(ctx, enabled=True)


@register("gacha_off")
async def handle_gacha_off(ctx: Ctx) -> None:
    await _switch_gacha(ctx, enabled=False)
