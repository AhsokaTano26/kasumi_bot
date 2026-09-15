"""Tsugu BanGDream Bot 的 QQ 官方 Bot 前端。"""

from __future__ import annotations

from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="tsugu",
    description="Tsugu BanGDream Bot 的 QQ 官方 Bot 前端",
    usage="发送「help」查看全部指令",
    config=Config,
    supported_adapters={"~onebot.v11", "~qq"},
)

config = get_plugin_config(Config)

import tsugu_api_async

tsugu_api_async.settings.backend_url = config.tsugu_backend_url
tsugu_api_async.settings.userdata_backend_url = config.tsugu_data_backend_url
tsugu_api_async.settings.timeout = config.tsugu_timeout
tsugu_api_async.settings.max_retries = config.tsugu_retries
tsugu_api_async.settings.proxy = config.tsugu_proxy
tsugu_api_async.settings.backend_proxy = config.tsugu_backend_proxy
tsugu_api_async.settings.userdata_backend_proxy = config.tsugu_data_backend_proxy
tsugu_api_async.settings.use_easy_bg = config.tsugu_use_easy_bg
tsugu_api_async.settings.compress = config.tsugu_compress
