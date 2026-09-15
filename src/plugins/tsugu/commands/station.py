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

    # 房间列表为空时上游客户端会短路返回字面量 "myc"，不请求 /roomList；
    # 后端 drawRoomList 对空列表也返回同一个 "myc"。实测公共后端：
    #   room_list([]) -> [{'type': 'string', 'string': 'myc'}]
    # 即空列表最终展示的就是 "myc"，与本移植版行为一致，故这里不做特判。
    # （注意该路由的 notEmpty 校验并不会拦住空数组——实测未触发 400。）
    await ctx.reply(await api.render_room_list(rooms))
