"""命令分派表与执行上下文。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..sender import Response, send_result

if TYPE_CHECKING:
    from nonebot.adapters.qq import Bot
    from nonebot.matcher import Matcher

    from ..user import PendingBind


@dataclass
class Ctx:
    """一次命令执行的上下文。

    把处理器需要的一切显式传进来，避免处理器再去做全局查找。
    """

    matcher: type[Matcher]
    bot: "Bot"
    event: Any
    user_id: str
    group_openid: str | None
    args: list[str]
    head: str
    at_user_id: str | None
    max_messages: int
    # PendingBind 在 TYPE_CHECKING 下导入；本文件有 from __future__ import
    # annotations，注解不会在运行时求值，所以不用加引号。
    pending: PendingBind | None = None

    async def reply(self, items: Response) -> None:
        """发送后端响应，自动处理条数上限。"""
        await send_result(
            self.matcher,
            items,
            limit=self.max_messages,
            at_user_id=self.at_user_id,
        )

    async def reply_text(self, text: str) -> None:
        """发送一条纯文本并结束本次处理。"""
        await self.matcher.finish(text)

    async def reply_error(self, text: str) -> None:
        """发送一条错误文本并结束本次处理。"""
        await self.matcher.finish(text)

    def local_only(self) -> bool:
        """当前是否在私聊里（群级设置类命令需要这个判断）。"""
        return self.group_openid is None


Handler = Callable[[Ctx], Awaitable[None]]
"""命令处理器。"""

HANDLERS: dict[str, Handler] = {}
"""命令 ID -> 处理器。各命令模块在 import 时注册。"""


def register(command: str) -> Callable[[Handler], Handler]:
    """把处理器登记到分派表的装饰器。"""

    def decorator(func: Handler) -> Handler:
        HANDLERS[command] = func
        return func

    return decorator


def _load_command_modules() -> None:
    """导入本包下所有命令模块，触发它们的 @register 装饰器。

    必须放在 Ctx / register 定义之后：子模块会 `from . import Ctx, register`，
    提前导入会拿到尚未定义的名字。用 iter_modules 自动发现而不是逐条 import，
    这样以后新增命令模块不用回来改这里。
    """
    from importlib import import_module
    from pkgutil import iter_modules

    for module in iter_modules(__path__):
        if not module.name.startswith("_"):
            import_module(f"{__name__}.{module.name}")


_load_command_modules()
