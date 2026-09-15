"""把 Tsugu 后端的响应列表翻译成 QQ 消息并发送。

后端所有查询接口统一返回 [{type: 'string'|'base64', string: ...}]。
QQ 官方平台限制同一个 msg_id 最多回复 5 条被动消息，所以不能一对一地发，
需要合并文本、并把超出部分截断。
"""

from __future__ import annotations

from base64 import b64decode
from typing import TYPE_CHECKING

from nonebot.adapters.qq import Message, MessageSegment

if TYPE_CHECKING:
    from nonebot.matcher import Matcher

Response = list[dict[str, str]]
"""Tsugu 后端的统一响应结构。"""

Part = str | bytes
"""一条待发送的消息：str 是文本，bytes 是图片二进制。"""


def split_messages(items: Response, limit: int) -> list[Part]:
    """把后端响应合并、截断成待发送的消息序列。

    连续的 string 段合并为一条文本消息；每个 base64 段单独作为一条图片消息。
    合并后的条数超过 limit 时，只保留前 limit - 1 条，末尾追加一条截断提示，
    这样总条数仍不超过 limit。
    """
    limit = max(limit, 1)

    parts: list[Part] = []
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            parts.append("".join(buffer))
            buffer.clear()

    for item in items:
        if item.get("type") == "base64":
            flush()
            parts.append(b64decode(item["string"]))
        else:
            buffer.append(item.get("string", ""))
    flush()

    if len(parts) <= limit:
        return parts
    return [*parts[: limit - 1], f"结果过长，仅显示前 {limit - 1} 项"]


def build_message(part: Part) -> Message:
    """把单个 Part 组装成 QQ 消息。

    图片用 file_image 产生 file_type=1 的 LocalAttachment，适配器据此识别为图片。

    这里不传 file_name，但它**不影响走哪条上传路径**：
    适配器的 `_extract_qq_media` 只在 `file_data` 超过 10MB 时才往 kwargs 里塞
    `file_name`，`send_to_group` 再按「kwargs 里有没有 file_name」在
    `post_group_upload`（分块）与 `post_group_files`（普通）之间二选一。
    所以约 310KB 的图片**传不传 file_name 都走普通上传**；反过来，任何 ≥10MB 的
    图片都会自动走分块上传，这一点本模块无法干预。
    """
    if isinstance(part, str):
        return Message(MessageSegment.text(part))
    return Message(MessageSegment.file_image(part))


async def send_result(
    matcher: "Matcher",
    items: Response,
    *,
    limit: int,
    at_user_id: str | None = None,
) -> None:
    """按顺序发出全部消息。

    msg_id 与自增的 msg_seq 由 nonebot-adapter-qq 的 Bot.send 自动填充，
    这里不要自己维护，也不要跨事件复用同一个 matcher 的发送。
    """
    parts = split_messages(items, limit)
    if not parts:
        return

    for index, part in enumerate(parts):
        message = build_message(part)
        if index == 0 and at_user_id is not None:
            message = Message(MessageSegment.mention_user(at_user_id)) + " " + message
        await matcher.send(message)
