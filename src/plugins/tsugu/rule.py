"""QQ 官方 Bot 触发层。

QQ 群里 Bot 只能收到 @ 了它的消息，而 @ 会被适配器解析成 MentionUser 段。
nonebot 的 TrieRule.get_value 只看 message[0]，遇到非文本段直接放弃匹配，
所以标准的 on_command 在群里完全失效，只能自己实现分派。

本模块全部是纯函数，不依赖 NoneBot 运行时，可直接被探针脚本 import。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

CAR_PATTERN = re.compile(r"^(\d{5,6})(.*)$", re.DOTALL)
MODE_SHORTCUT = re.compile(r"^(.+服)模式$")
STATUS_SHORTCUT = re.compile(r"^(.+服)玩家状态$")


@dataclass(frozen=True)
class Match:
    """一次成功的命令匹配。"""

    command: str
    """命令 ID，如 search_card。"""

    head: str
    """实际命中的命令头，用于生成帮助提示。"""

    args: list[str] = field(default_factory=list)
    """按空白切分后的参数。"""


def normalize(text: str) -> str:
    """剥掉首尾空白。

    event.get_message().extract_plain_text() 会去掉 @bot 但留下前导空格。
    """
    return text.strip()


def build_head_table(heads: Iterable[tuple[str, str]]) -> dict[str, str]:
    """把 (命令头, 命令ID) 按命令头长度降序排成查找表。

    保持插入顺序很关键：dict 在 3.7+ 保证插入顺序，遍历时「查卡面」
    一定先于「查卡」被尝试，前缀冲突由此消解。
    """
    ordered = sorted(heads, key=lambda pair: len(pair[0]), reverse=True)
    return dict(ordered)


def match_command(
    text: str,
    table: dict[str, str],
    *,
    no_space: bool = False,
) -> Match | None:
    """在 text 里匹配命令头。没有命中返回 None。

    no_space=False（默认）时命令头之后必须是空白或字符串结束；
    no_space=True 时额外允许「查卡947」这种无空格写法。
    """
    for head, command in table.items():
        if not text.startswith(head):
            continue
        rest = text[len(head) :]
        if rest and not no_space and not rest[0].isspace():
            continue
        return Match(command=command, head=head, args=rest.split())
    return None


def apply_shortcut(text: str) -> str:
    """把 mainline Tsugu 的两个 shortcut 正则改写成等价的标准命令。

    日服模式      -> 主服务器 日服
    国服玩家状态  -> 玩家状态 国服
    """
    if matched := MODE_SHORTCUT.match(text):
        return f"主服务器 {matched.group(1)}"
    if matched := STATUS_SHORTCUT.match(text):
        return f"玩家状态 {matched.group(1)}"
    return text


def match_car(
    text: str,
    car_keywords: Iterable[str],
    fake_keywords: Iterable[str],
) -> tuple[int, str] | None:
    """识别车牌消息。

    规则：以 5 或 6 位数字开头，其余部分包含至少一个车牌关键词，
    且不包含任何反关键词。命中返回 (房间号, 房间号之后的原文)。
    """
    matched = CAR_PATTERN.match(text)
    if matched is None:
        return None

    rest = matched.group(2)
    lowered = rest.lower()
    if not any(keyword in lowered for keyword in car_keywords):
        return None
    if any(keyword in lowered for keyword in fake_keywords):
        return None
    return int(matched.group(1)), rest


def get_group_openid(event: object) -> str | None:
    """取出群 openid；私聊事件没有这个字段。"""
    return getattr(event, "group_openid", None)
