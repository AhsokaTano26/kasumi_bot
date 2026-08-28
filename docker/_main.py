import nonebot

from qq_config import configure_qq_bots

configure_qq_bots()

import bot  # noqa: F401

app = nonebot.get_asgi()
