"""用户设置类命令：绑定、解绑、主服务器、显示服务器、玩家状态、车牌转发。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .. import api, user
from .. import constants as const
from . import Ctx, register

if TYPE_CHECKING:
    from tsugu_api_core._typing import ServerId


@register("bind_player")
async def handle_bind_player(ctx: Ctx) -> None:
    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)

    if ctx.args:
        try:
            server = await api.resolve_server(ctx.args[0])
        except ValueError as exc:
            await ctx.reply_error(str(exc))
            return
    else:
        server = tsugu_user.main_server

    try:
        code = await api.request_bind_code(ctx.user_id)
    except api.UserDataError as exc:
        await ctx.reply_error(str(exc))
        return

    user.pending[ctx.user_id] = user.PendingBind(action="bind", server=server)
    await ctx.reply_text(user.build_bind_prompt(server, code))


@register("bind_reply")
async def handle_bind_reply(ctx: Ctx) -> None:
    """绑定流程的第二步。由分派器在发现待处理流程时调用。

    分派器只 `get` 不 `pop`，所以**只有真正成功时**才在这里清掉待处理状态；
    中途失败（玩家 ID 不合法、验证码没对上）都保留状态让用户重试，
    直到成功或超过 tsugu_bind_timeout。
    """
    pending = ctx.pending
    if pending is None:
        return

    # 解绑不需要玩家 ID，用户发任意消息即可
    if pending.action == "unbind":
        if pending.player_id is None:
            return
        try:
            message = await api.verify_bind(
                ctx.user_id, pending.server, pending.player_id, "unbind"
            )
        except api.UserDataError as exc:
            await ctx.reply_error(str(exc))
            return
        user.pending.pop(ctx.user_id, None)
        await ctx.reply_text(message)
        return

    player_id_text = ctx.args[0].strip() if ctx.args else ""
    if not player_id_text.isdecimal():
        await ctx.reply_text(const.ERR_PLAYER_ID_INVALID)
        return

    player_id = int(player_id_text)
    try:
        await api.verify_bind(ctx.user_id, pending.server, player_id, "bind")
    except api.UserDataError as exc:
        await ctx.reply_error(str(exc))
        return

    user.pending.pop(ctx.user_id, None)
    await ctx.matcher.send(
        f"绑定 {user.server_name(pending.server)} 玩家 {player_id} 成功，"
        "正在生成玩家状态图片"
    )
    await ctx.reply(await api.search_player(player_id, pending.server))


@register("unbind_player")
async def handle_unbind_player(ctx: Ctx) -> None:
    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)

    if ctx.args:
        try:
            server = await api.resolve_server(ctx.args[0])
        except ValueError as exc:
            await ctx.reply_error(str(exc))
            return
    else:
        server = tsugu_user.main_server

    try:
        player = user.pick_player(tsugu_user, server=server)
    except ValueError as exc:
        await ctx.reply_error(str(exc))
        return

    try:
        code = await api.request_bind_code(ctx.user_id)
    except api.UserDataError as exc:
        await ctx.reply_error(str(exc))
        return

    player_id = player["playerId"]
    user.pending[ctx.user_id] = user.PendingBind(
        action="unbind", server=server, player_id=player_id
    )
    await ctx.reply_text(
        f"正在解除绑定来自 {user.server_name(server)} 账号 玩家ID: {player_id} \n"
        "请将你的\n"
        "评论(个性签名)\n"
        "或者\n"
        "你的当前使用的卡组的卡组名(乐队编队名称)\n"
        "改为以下数字后，发送任意消息继续\n"
        f"{code}"
    )


@register("main_server")
async def handle_main_server(ctx: Ctx) -> None:
    if not ctx.args:
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    try:
        server = await api.resolve_server(ctx.args[0])
    except ValueError as exc:
        await ctx.reply_error(str(exc))
        return

    error = await api.change_user(ctx.user_id, {"mainServer": server})
    if error:
        await ctx.reply_error(error)
        return
    await ctx.reply_text(f"已切换到{user.server_name(server)}模式")


@register("display_servers")
async def handle_display_servers(ctx: Ctx) -> None:
    if not ctx.args:
        await ctx.reply_error("错误: 请指定至少一个服务器")
        return

    servers: list[ServerId] = []
    for name in ctx.args:
        try:
            server = await api.resolve_server(name)
        except ValueError:
            await ctx.reply_error("错误: 指定了不存在的服务器")
            return
        if server in servers:
            await ctx.reply_error("错误: 指定了重复的服务器")
            return
        servers.append(server)

    error = await api.change_user(ctx.user_id, {"displayedServerList": servers})
    if error:
        await ctx.reply_error(error)
        return
    await ctx.reply_text(
        "成功切换默认显示服务器顺序: "
        + ", ".join(user.server_name(server) for server in servers)
    )


@register("player_status")
async def handle_player_status(ctx: Ctx) -> None:
    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)

    index: int | None = None
    server: ServerId | None = None

    if ctx.args:
        if ctx.args[0].isdecimal():
            index = int(ctx.args[0])
            if len(ctx.args) > 1:
                try:
                    server = await api.resolve_server(ctx.args[1])
                except ValueError as exc:
                    await ctx.reply_error(str(exc))
                    return
        else:
            try:
                server = await api.resolve_server(ctx.args[0])
            except ValueError as exc:
                await ctx.reply_error(str(exc))
                return

    try:
        player = user.pick_player(tsugu_user, server=server, index=index)
    except ValueError as exc:
        await ctx.reply_error(str(exc))
        return

    await ctx.reply(await api.search_player(player["playerId"], player["server"]))


@register("player_list")
async def handle_player_list(ctx: Ctx) -> None:
    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply_text(user.build_player_list_text(tsugu_user))


@register("player_index")
async def handle_player_index(ctx: Ctx) -> None:
    if not ctx.args or not ctx.args[0].isdecimal():
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    index = int(ctx.args[0])
    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    if index < 1 or index > len(tsugu_user.user_player_list):
        await ctx.reply_error(const.ERR_INDEX_INVALID)
        return

    error = await api.change_user(ctx.user_id, {"userPlayerIndex": index - 1})
    if error:
        await ctx.reply_error(error)
        return
    await ctx.reply_text(f"已切换至绑定信息ID: {index}")


async def _toggle_forward(ctx: Ctx, *, enabled: bool) -> None:
    error = await api.change_user(ctx.user_id, {"shareRoomNumber": enabled})
    if error:
        await ctx.reply_error(error)
        return
    await ctx.reply_text("已开启车牌转发" if enabled else "已关闭车牌转发")


@register("open_forward")
async def handle_open_forward(ctx: Ctx) -> None:
    await _toggle_forward(ctx, enabled=True)


@register("close_forward")
async def handle_close_forward(ctx: Ctx) -> None:
    await _toggle_forward(ctx, enabled=False)
