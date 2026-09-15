"""车牌查询：ycm。"""

from __future__ import annotations

from .. import api
from . import Ctx, register


@register("ycm")
async def handle_ycm(ctx: Ctx) -> None:
    try:
        rooms = await api.query_all_rooms()
    except api.UserDataError as exc:
        await ctx.reply_error(str(exc))
        return

    if ctx.args:
        keyword = " ".join(ctx.args)
        rooms = [room for room in rooms if keyword in room.get("rawMessage", "")]
        if not rooms:
            await ctx.reply_text(f"没有找到包含 {keyword} 的房间")
            return

    # 房间列表为空时后端自己会返回提示文本，这里不用特殊处理
    await ctx.reply(await api.render_room_list(rooms))
