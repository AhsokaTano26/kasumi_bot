"""查曲、查谱面、随机曲、查询分数表。"""

from __future__ import annotations

from .. import api, user
from .. import constants as const
from . import Ctx, register


@register("search_song")
async def handle_search_song(ctx: Ctx) -> None:
    if not ctx.args:
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(
        await api.search_song(tsugu_user.displayed_server_list, " ".join(ctx.args))
    )


@register("song_chart")
async def handle_song_chart(ctx: Ctx) -> None:
    if not ctx.args or not ctx.args[0].isdecimal():
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    song_id = int(ctx.args[0])
    difficulty_id = const.DEFAULT_DIFFICULTY_ID
    if len(ctx.args) > 1:
        try:
            difficulty_id = await api.resolve_difficulty(ctx.args[1])
        except ValueError as exc:
            await ctx.reply_error(str(exc))
            return

    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(
        await api.song_chart(tsugu_user.displayed_server_list, song_id, difficulty_id)
    )


@register("song_random")
async def handle_song_random(ctx: Ctx) -> None:
    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(await api.song_random(tsugu_user.main_server, " ".join(ctx.args)))


@register("song_meta")
async def handle_song_meta(ctx: Ctx) -> None:
    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)

    server = tsugu_user.main_server
    if ctx.args:
        try:
            server = await api.resolve_server(ctx.args[0])
        except ValueError as exc:
            await ctx.reply_error(str(exc))
            return

    await ctx.reply(await api.song_meta(tsugu_user.displayed_server_list, server))
