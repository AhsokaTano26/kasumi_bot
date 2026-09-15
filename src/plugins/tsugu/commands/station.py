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

    # 上游客户端在房间列表为空时会短路返回字面量 "myc"，不请求 /roomList；
    # 后端 commandRoomList 里也有同样的分支，但那条路由的 notEmpty 校验会先把
    # 空数组挡成 400。本移植版刻意不做这个特判，空列表照常交给后端。
    await ctx.reply(await api.render_room_list(rooms))
