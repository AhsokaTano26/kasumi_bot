"""车牌自动转发。

群聊里 Bot 只能收到 @ 了它的消息，所以「5/6 位数字开头」的车牌在群里根本
收不到；私聊里能正常工作。逻辑保持完整，将来拿到全量消息权限即自动生效。
"""

from __future__ import annotations

from typing import Any

import nonebot

from . import api
from . import constants as const
from .rule import match_car


async def maybe_forward(event: Any, user_id: str, text: str) -> bool:
    """识别并提交车牌。命中并提交成功返回 True，应当终止后续命令分派。"""
    car = match_car(text, const.CAR_KEYWORDS, const.FAKE_KEYWORDS)
    if car is None:
        return False

    number, _rest = car
    try:
        raw_user = await api.load_user(user_id)
    except api.UserDataError as exc:
        nonebot.logger.debug(f"车牌识别：读取用户数据失败 {exc}")
        return False

    if not raw_user.get("shareRoomNumber"):
        nonebot.logger.debug("车牌识别：该用户未开启车牌转发")
        return False

    from nonebot import get_plugin_config

    from .config import Config

    config = get_plugin_config(Config)
    # 昵称挂在 event.author.username 上（GroupMemberAuthor 与 FriendAuthor 都有），
    # 事件本身没有顶层 username 字段
    user_name = getattr(getattr(event, "author", None), "username", None) or user_id
    error = await api.submit_room_number(
        number,
        text,
        user_id,
        str(user_name),
        config.tsugu_bandori_station_token,
    )
    if error:
        nonebot.logger.warning(f"车牌识别：提交失败 {error}")
        return False

    nonebot.logger.debug(f"车牌识别：已提交房间 {number}")
    return True
