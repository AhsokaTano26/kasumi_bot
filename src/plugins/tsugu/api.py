"""Tsugu 后端调用封装。

查询类接口在后端统一返回 [{type: 'string'|'base64', string: ...}]，业务错误
也是数组里的一个 string 段。这里把异常也收敛成同样的形状，于是调用方只需
处理一种返回类型。
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, cast

import nonebot
import tsugu_api_async
from tsugu_api_core._typing import (
    PartialTsuguUser,
    ServerId,
    _BindingAction,
    _DifficultyId,
    _Response,
    _Room,
    _TsuguUser,
)
from tsugu_api_core.exception import (
    BadRequestError,
    FailedException,
    HTTPStatusError,
    TsuguException,
)

from . import constants as const

if TYPE_CHECKING:
    from collections.abc import Awaitable, Sequence

Response = _Response
"""Tsugu 后端的统一响应结构，直接用库声明的类型。"""


class UserDataError(Exception):
    """用户数据接口返回失败。str(exc) 是可直接展示的中文文案。"""


def _error(text: str) -> Response:
    return [{"type": "string", "string": text}]


def _platform() -> str:
    """读取配置里的平台标识。"""
    from nonebot import get_plugin_config

    from .config import Config

    return get_plugin_config(Config).tsugu_platform


def describe_error(exc: BaseException) -> str:
    """把 tsugu_api 抛出的异常翻译成给用户看的中文文案。"""
    if isinstance(exc, BadRequestError):
        return const.HTTP_ERROR_TEXTS[400]
    if isinstance(exc, FailedException):
        if exc.status_code == HTTPStatus.UNPROCESSABLE_ENTITY:
            return f"错误: 无效的请求 ({exc.data})"
        return const.HTTP_ERROR_TEXTS.get(exc.status_code, str(exc.data))

    if isinstance(exc, HTTPStatusError):
        return const.ERR_NETWORK

    if isinstance(exc, TsuguException):
        # 基类 TsuguException 的 msg 本身就是给用户看的中文
        # （如车站的 RoomQueryFailure / RoomSubmitFailure）
        return str(exc)

    return const.ERR_NETWORK


async def _query(coro: Awaitable[Response]) -> Response:
    """执行一次后端查询，把任何异常收敛成错误文本响应。"""
    try:
        return await coro
    except Exception as exc:  # noqa: BLE001 - 网络/超时/解析错误都要收敛成文案
        nonebot.logger.opt(exception=exc).debug("Tsugu 后端查询失败")
        return _error(describe_error(exc))


# ---- 名称解析 ----


async def resolve_server(name: str) -> ServerId:
    """把服务器名解析成 ServerId。

    先查本地表（英文代号 / 中文全名 / 数字），未命中再走后端模糊搜索。
    失败抛 ValueError，文案已可直接展示。
    """
    # 表里所有键都是小写，所以只查小写形式即可覆盖精确输入
    if (server_id := const.SERVER_NAME_TO_ID.get(name.lower())) is not None:
        return server_id

    try:
        found = (await tsugu_api_async.fuzzy_search(name))["data"].get("server", [])
    except Exception as exc:
        nonebot.logger.opt(exception=exc).debug("服务器名模糊搜索失败")
        raise ValueError(const.ERR_SERVER_NOT_FOUND) from exc

    # 后端模糊搜索返回的是无类型的 str | int，这里收窄成 ServerId
    if not found or found[0] not in const.SERVER_ID_TO_NAME:
        raise ValueError(const.ERR_SERVER_NOT_FOUND)
    return cast("ServerId", found[0])


async def resolve_difficulty(name: str) -> _DifficultyId:
    """把难度名解析成 DifficultyId。失败抛 ValueError，文案已可直接展示。"""
    if (difficulty_id := const.DIFFICULTY_NAMES.get(name.lower())) is not None:
        return difficulty_id

    try:
        found = (await tsugu_api_async.fuzzy_search(name))["data"].get("difficulty", [])
    except Exception as exc:
        nonebot.logger.opt(exception=exc).debug("难度名模糊搜索失败")
        raise ValueError(const.ERR_DIFFICULTY_NOT_FOUND) from exc

    if not found or found[0] not in (0, 1, 2, 3, 4):
        raise ValueError(const.ERR_DIFFICULTY_NOT_FOUND)
    return cast("_DifficultyId", found[0])


# ---- 用户数据 ----


async def load_user(user_id: str) -> _TsuguUser:
    """读取用户数据。后端对不存在的用户会自动创建。"""
    try:
        response = await tsugu_api_async.get_user_data(_platform(), user_id)
    except Exception as exc:
        nonebot.logger.opt(exception=exc).debug("读取用户数据失败")
        raise UserDataError(describe_error(exc)) from exc

    if response.get("status") != "success":
        raise UserDataError(str(response.get("data", "错误: 获取用户数据失败")))
    return response["data"]


async def change_user(user_id: str, update: PartialTsuguUser) -> str | None:
    """写入用户数据。成功返回 None，失败返回可直接展示的错误文案。"""
    try:
        response = await tsugu_api_async.change_user_data(_platform(), user_id, update)
    except Exception as exc:  # noqa: BLE001 - 网络/超时/解析错误都要收敛成文案
        nonebot.logger.opt(exception=exc).debug("写入用户数据失败")
        return describe_error(exc)

    if response.get("status") != "success":
        return str(response.get("data", "错误: 修改用户数据失败"))
    return None


async def request_bind_code(user_id: str) -> int:
    """申请绑定验证码。"""
    try:
        response = await tsugu_api_async.bind_player_request(_platform(), user_id)
    except Exception as exc:
        nonebot.logger.opt(exception=exc).debug("申请绑定验证码失败")
        raise UserDataError(describe_error(exc)) from exc

    if response.get("status") != "success":
        raise UserDataError(str(response.get("data", "错误: 申请验证码失败")))
    return int(response["data"]["verifyCode"])


async def verify_bind(
    user_id: str, server: ServerId, player_id: int, action: _BindingAction
) -> str:
    """提交绑定或解绑验证。返回后端给的提示文本。"""
    try:
        response = await tsugu_api_async.bind_player_verification(
            _platform(), user_id, server, player_id, action
        )
    except Exception as exc:
        nonebot.logger.opt(exception=exc).debug("绑定验证失败")
        raise UserDataError(describe_error(exc)) from exc

    if response.get("status") != "success":
        raise UserDataError(str(response.get("data", "错误: 绑定验证失败")))
    return str(response["data"])


# ---- 查询接口 ----


async def search_card(servers: Sequence[ServerId], text: str) -> Response:
    return await _query(tsugu_api_async.search_card(servers, text=text))


async def card_illustration(card_id: int) -> Response:
    return await _query(tsugu_api_async.get_card_illustration(card_id))


async def search_character(servers: Sequence[ServerId], text: str) -> Response:
    return await _query(tsugu_api_async.search_character(servers, text=text))


async def search_event(servers: Sequence[ServerId], text: str) -> Response:
    return await _query(tsugu_api_async.search_event(servers, text=text))


async def search_gacha(servers: Sequence[ServerId], gacha_id: int) -> Response:
    return await _query(tsugu_api_async.search_gacha(servers, gacha_id))


async def search_song(servers: Sequence[ServerId], text: str) -> Response:
    return await _query(tsugu_api_async.search_song(servers, text=text))


async def song_chart(
    servers: Sequence[ServerId], song_id: int, difficulty_id: _DifficultyId
) -> Response:
    return await _query(tsugu_api_async.song_chart(servers, song_id, difficulty_id))


async def song_random(server: ServerId, text: str) -> Response:
    return await _query(tsugu_api_async.song_random(server, text=text))


async def song_meta(servers: Sequence[ServerId], server: ServerId) -> Response:
    return await _query(tsugu_api_async.song_meta(servers, server))


async def event_stage(
    server: ServerId, event_id: int | None, *, meta: bool
) -> Response:
    return await _query(tsugu_api_async.event_stage(server, event_id, meta))


async def search_player(player_id: int, server: ServerId) -> Response:
    return await _query(tsugu_api_async.search_player(player_id, server))


async def gacha_simulate(
    server: ServerId, times: int | None, gacha_id: int | None
) -> Response:
    return await _query(tsugu_api_async.gacha_simulate(server, times, gacha_id))


async def cutoff_detail(server: ServerId, tier: int, event_id: int | None) -> Response:
    return await _query(tsugu_api_async.cutoff_detail(server, tier, event_id))


async def cutoff_all(server: ServerId, event_id: int | None) -> Response:
    return await _query(tsugu_api_async.cutoff_all(server, event_id))


async def cutoff_history(server: ServerId, tier: int, event_id: int | None) -> Response:
    return await _query(
        tsugu_api_async.cutoff_list_of_recent_event(server, tier, event_id)
    )


async def query_all_rooms() -> list[_Room]:
    """车站里的全部房间号。

    注意这个接口不返回 Response 列表而是房间字典列表，为了和查询接口
    区分开，失败时抛 UserDataError 而不是返回错误文本段。
    """
    try:
        response = await tsugu_api_async.station_query_all_room()
    except Exception as exc:
        nonebot.logger.opt(exception=exc).debug("查询车站失败")
        raise UserDataError(describe_error(exc)) from exc

    if response.get("status") != "success":
        raise UserDataError(str(response.get("data", "错误: 查询车站失败")))
    return list(response["data"])


async def render_room_list(rooms: list[_Room]) -> Response:
    """把房间列表交给后端画成图片。"""
    return await _query(tsugu_api_async.room_list(rooms))


async def submit_room_number(
    number: int,
    raw_message: str,
    user_id: str,
    user_name: str,
    bandori_station_token: str | None,
) -> str:
    """提交车牌到车站。返回空串表示成功，否则是可直接展示的错误文案。"""
    try:
        response = await tsugu_api_async.station_submit_room_number(
            number,
            raw_message,
            _platform(),
            user_id,
            user_name,
            bandori_station_token=bandori_station_token,
        )
    except Exception as exc:  # noqa: BLE001 - 网络/超时/解析错误都要收敛成文案
        nonebot.logger.opt(exception=exc).debug("提交车牌失败")
        return describe_error(exc)

    if response.get("status") != "success":
        return str(response.get("data", "错误: 提交车牌失败"))
    return ""
