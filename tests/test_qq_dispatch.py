"""QQ 命令经过适配器预处理后应正确分派并回复。"""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

import nonebot
from nonebot.adapters.qq import Adapter, Bot
from nonebot.adapters.qq.config import BotInfo
from nonebot.adapters.qq.models import Dispatch, PostGroupMessagesReturn, User


class QQDispatchTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime = TemporaryDirectory(prefix="kasumi-dispatch-tests-")
        cls.addClassCleanup(cls.runtime.cleanup)
        previous_cwd = Path.cwd()
        try:
            os.chdir(cls.runtime.name)
            nonebot.init(
                driver="~fastapi+~httpx",
                command_start={"", "/"},
                localstore_use_cwd=True,
                sqlalchemy_database_url="sqlite+aiosqlite:///test.sqlite3",
                alembic_startup_check=False,
                log_level="WARNING",
            )
            plugin = nonebot.load_plugin("src.plugins.tsugu")
            if plugin is None:
                raise RuntimeError("Tsugu plugin failed to load")
        finally:
            os.chdir(previous_cwd)
        cls.adapter = Adapter(nonebot.get_driver())

    async def asyncSetUp(self) -> None:
        self.bot = Bot(
            self.adapter,
            "test-app",
            BotInfo(id="test-app", secret="test-secret", use_websocket=False),
        )
        self.bot.self_info = User(id="test_bot", username="Kasumi", bot=True)

    async def send_command(
        self,
        content: str,
        *,
        mentioned_id: str | None = "test_bot",
        quoted: bool = False,
        event_type: str = "GROUP_MESSAGE_CREATE",
    ) -> list[dict[str, Any]]:
        data: dict[str, Any] = {
            "id": "test-message",
            "content": content,
            "timestamp": "2026-10-13T00:00:00+08:00",
            "author": {
                "id": "test-user",
                "member_openid": "test-user",
                "bot": False,
                "member_role": "member",
            },
            "group_id": "test-group",
            "group_openid": "test-group",
        }
        if mentioned_id is not None:
            data["mentions"] = [
                {
                    "scope": "single",
                    "bot": True,
                    "id": mentioned_id,
                    "is_you": mentioned_id == "test_bot",
                    "member_openid": mentioned_id,
                    "username": "Kasumi",
                }
            ]
        if quoted:
            data.update(
                message_type=103,
                message_scene={"ext": ["ref_msg_idx=quoted"], "source": "group"},
                msg_elements=[
                    {
                        "content": "prior bot reply",
                        "message_type": 0,
                        "msg_idx": "quoted",
                        "author": {"id": "test_bot", "bot": True, "username": "Kasumi"},
                    }
                ],
            )
        event = Adapter.payload_to_event(
            Dispatch.model_validate(
                {"op": 0, "s": 1, "t": event_type, "id": "test-event", "d": data}
            )
        )
        replies: list[dict[str, Any]] = []

        async def capture_api(
            _adapter: Adapter, _bot: Bot, api: str, **kwargs: Any
        ) -> PostGroupMessagesReturn:
            self.assertEqual(api, "post_group_messages")
            self.assertEqual(kwargs["group_openid"], "test-group")
            replies.append(kwargs)
            return PostGroupMessagesReturn(id="test-reply")

        # 只拦截外部 QQ API；适配器预处理、NoneBot 分派、帮助生成和发送均照常执行。
        with patch.object(Adapter, "_call_api", capture_api):
            await self.bot.handle_event(event)
        return replies

    async def test_slash_help_sends_command_list(self) -> None:
        replies = await self.send_command("/help ")
        self.assertEqual(len(replies), 1)
        self.assertIn("Kasumi 命令帮助", replies[0]["markdown"].content)

    async def test_slash_help_resolves_prefixed_command_name(self) -> None:
        replies = await self.send_command("/help /查卡")
        self.assertEqual(len(replies), 1)
        self.assertIn("根据关键词或卡牌ID查询卡片信息", replies[0]["markdown"].content)

    async def test_unmentioned_help_is_ignored(self) -> None:
        self.assertEqual(await self.send_command("/help", mentioned_id=None), [])

    async def test_help_mentioning_another_bot_is_ignored(self) -> None:
        replies = await self.send_command("<@other_bot> /help", mentioned_id="other_bot")
        self.assertEqual(replies, [])

    async def test_reply_only_help_is_ignored(self) -> None:
        self.assertEqual(await self.send_command("<@test_bot> /help", quoted=True), [])

    async def test_reply_with_explicit_mention_sends_help(self) -> None:
        replies = await self.send_command("<@test_bot> <@test_bot> /help", quoted=True)
        self.assertEqual(len(replies), 1)
        self.assertIn("Kasumi 命令帮助", replies[0]["markdown"].content)

    async def test_at_message_event_sends_help_without_mention_metadata(self) -> None:
        replies = await self.send_command(
            "/help", mentioned_id=None, event_type="GROUP_AT_MESSAGE_CREATE"
        )
        self.assertEqual(len(replies), 1)
        self.assertIn("Kasumi 命令帮助", replies[0]["markdown"].content)


if __name__ == "__main__":
    unittest.main()
