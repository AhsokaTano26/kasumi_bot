"""用户数据模型、玩家绑定选择规则与绑定流程状态。

平台标识固定为配置里的 TSUGU_PLATFORM（默认 "red"），与官方 Tsugu QQ Bot
共用同一份用户数据命名空间。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from . import api
from . import constants as const

if TYPE_CHECKING:
    from nonebot.matcher import Matcher
    from tsugu_api_core._typing import (
        ServerId,
        _BindingAction,
        _TsuguUser,
        _UserPlayerInList,
    )


@dataclass
class User:
    """用户数据的可读视图。字段名与后端 tsuguUser 一一对应。"""

    main_server: ServerId = 3
    displayed_server_list: list[ServerId] = field(default_factory=lambda: [3, 0])
    share_room_number: bool = True
    user_player_index: int = 0
    user_player_list: list[_UserPlayerInList] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: _TsuguUser) -> "User":
        # 下标取值而非 .get(默认值)：_TsuguUser 把字段都声明为必填，给不存在的
        # 字段编默认值只会掩盖后端契约被破坏这件事。
        return cls(
            main_server=raw["mainServer"],
            displayed_server_list=list(raw["displayedServerList"]),
            share_room_number=raw["shareRoomNumber"],
            user_player_index=raw["userPlayerIndex"],
            user_player_list=list(raw["userPlayerList"]),
        )


@dataclass
class PendingBind:
    """等待用户回复玩家 ID 的绑定流程。"""

    action: _BindingAction
    """'bind' 或 'unbind'。"""

    server: ServerId
    created_at: float = field(default_factory=time.monotonic)
    """创建时刻，用于超时判断。"""

    player_id: int | None = None
    """解绑时已确定要解绑的玩家；绑定时为 None。"""


pending: dict[str, PendingBind] = {}
"""用户 ID -> 待处理的绑定流程。进程内存，重启即失效，这是期望行为。"""


def server_name(server: ServerId) -> str:
    """服务器 ID 转中文名。"""
    return const.SERVER_ID_TO_NAME.get(server, str(server))


async def load_user_or_finish(matcher: type[Matcher], user_id: str) -> User:
    """读取用户数据；失败时直接结束本次回复。

    matcher.finish 会抛 FinishedException，所以成功路径以外不会返回。
    """
    try:
        raw = await api.load_user(user_id)
    except api.UserDataError as exc:
        await matcher.finish(str(exc))
        raise
    return User.from_raw(raw)


def pick_player(
    user: User, server: ServerId | None = None, index: int | None = None
) -> _UserPlayerInList:
    """按 mainline Tsugu 的规则选出要展示的玩家绑定。

    index 给定时按 1 起的序号取；否则先看默认索引那条是不是在目标服务器上，
    不是的话取列表中第一条属于目标服务器的绑定。失败抛 ValueError。
    """
    players = user.user_player_list
    if not players:
        raise ValueError(const.ERR_NOT_BOUND_ANY)

    if index is not None:
        if index < 1 or index > len(players):
            raise ValueError(const.ERR_INDEX_INVALID)
        return players[index - 1]

    target = user.main_server if server is None else server
    if 0 <= user.user_player_index < len(players):
        default_player = players[user.user_player_index]
        if default_player["server"] == target:
            return default_player

    for player in players:
        if player["server"] == target:
            return player

    raise ValueError(const.ERR_NOT_BOUND_ON_SERVER)


def build_player_list_text(user: User) -> str:
    """玩家状态列表命令的纯文本回复。"""
    lines: list[str] = []
    if not user.user_player_list:
        lines.append(const.ERR_NOT_BOUND_ANY)
    else:
        lines.append("已绑定玩家列表:")
        for index, player in enumerate(user.user_player_list, 1):
            lines.append(
                f"{index}. {server_name(player['server'])}: {player['playerId']}"
            )
        lines.append(f"当前默认玩家绑定信息ID: {user.user_player_index + 1}")

    lines.append(f"当前主服务器: {server_name(user.main_server)}")
    lines.append(
        "默认显示服务器顺序: "
        + ", ".join(server_name(server) for server in user.displayed_server_list)
    )
    return "\n".join(lines)


def build_bind_prompt(server: ServerId, code: int) -> str:
    """绑定流程第一步的引导文本，措辞与 mainline Tsugu 一致。"""
    return (
        f"正在绑定来自 {server_name(server)} 账号，请将你的\n"
        "评论(个性签名)\n"
        "或者\n"
        "你的当前使用的卡组的卡组名(乐队编队名称)\n"
        "改为以下数字后，直接发送你的玩家id\n"
        f"{code}"
    )
