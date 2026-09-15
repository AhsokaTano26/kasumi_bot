"""查玩家。"""

from __future__ import annotations

from .. import api, user
from .. import constants as const
from . import Ctx, register


@register("search_player")
async def handle_search_player(ctx: Ctx) -> None:
    if not ctx.args or not ctx.args[0].isdecimal():
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    player_id = int(ctx.args[0])

    server = None
    if len(ctx.args) > 1:
        try:
            server = await api.resolve_server(ctx.args[1])
        except ValueError as exc:
            await ctx.reply_error(str(exc))
            return

    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(
        await api.search_player(player_id, server or tsugu_user.main_server)
    )
