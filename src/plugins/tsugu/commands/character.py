"""查角色。"""

from __future__ import annotations

from .. import api, user
from .. import constants as const
from . import Ctx, register


@register("search_character")
async def handle_search_character(ctx: Ctx) -> None:
    if not ctx.args:
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(
        await api.search_character(tsugu_user.displayed_server_list, " ".join(ctx.args))
    )
