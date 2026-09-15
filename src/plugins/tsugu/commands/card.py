"""查卡与查卡面。"""

from __future__ import annotations

from .. import api, user
from .. import constants as const
from . import Ctx, register


@register("search_card")
async def handle_search_card(ctx: Ctx) -> None:
    if not ctx.args:
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(
        await api.search_card(tsugu_user.displayed_server_list, " ".join(ctx.args))
    )


@register("card_illustration")
async def handle_card_illustration(ctx: Ctx) -> None:
    if not ctx.args or not ctx.args[0].isdigit():
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    await ctx.reply(await api.card_illustration(int(ctx.args[0])))
