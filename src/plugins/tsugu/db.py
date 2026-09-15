"""群级设置的本地存储。

Tsugu 的用户数据 API 以用户为键，表达不了「本群」这个维度，所以群级设置
只能落本地。整个项目仅此一张表。
"""

from __future__ import annotations

from nonebot_plugin_orm import Model, get_session
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column


class GroupSetting(Model):
    """群级设置。"""

    __tablename__ = "tsugu_group_settings"

    group_openid: Mapped[str] = mapped_column(String(64), primary_key=True)
    gacha_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


async def is_gacha_enabled(group_openid: str) -> bool:
    """查不到该群的行时视为默认开启，只读操作不写库。"""
    session = get_session()
    async with session.begin():
        setting = await session.get(GroupSetting, group_openid)
        return True if setting is None else bool(setting.gacha_enabled)


async def set_gacha_enabled(group_openid: str, *, enabled: bool) -> None:
    """写入群级抽卡开关，不存在则插入。"""
    session = get_session()
    async with session.begin():
        setting = await session.get(GroupSetting, group_openid)
        if setting is None:
            session.add(GroupSetting(group_openid=group_openid, gacha_enabled=enabled))
        else:
            setting.gacha_enabled = enabled
