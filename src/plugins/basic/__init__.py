import random

from nonebot import get_plugin_config, on_command
from nonebot.adapters.qq import MessageEvent
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="basic",
    description="基础命令插件",
    usage="发送 /ping, /hello, /help 等命令",
    config=Config,
)

config = get_plugin_config(Config)

# Ping 命令
ping_cmd = on_command("ping", aliases={"ping"}, priority=10, block=True)


@ping_cmd.handle()
async def handle_ping(event: MessageEvent):
    await ping_cmd.finish("pong")


# 问候命令
hello_cmd = on_command("hello", aliases={"你好"}, priority=10, block=True)

HELLO_RESPONSES = [
    "你好！",
    "嗨！",
    "Hello！",
    "你好呀！",
    "嗨嗨！",
]


@hello_cmd.handle()
async def handle_hello(event: MessageEvent):
    response = random.choice(HELLO_RESPONSES)
    await hello_cmd.finish(response)


# 帮助命令
help_cmd = on_command("help", aliases={"帮助"}, priority=10, block=True)

HELP_TEXT = """可用命令列表：

基础命令：
/ping - 测试机器人响应
/hello 或 /你好 - 打招呼
/help 或 /帮助 - 显示此帮助信息

娱乐命令：
/random <最小值> <最大值> - 生成随机数
/joke 或 /笑话 - 听个笑话
/dice 或 /骰子 - 掷骰子
/guess - 猜数字游戏"""


@help_cmd.handle()
async def handle_help(event: MessageEvent):
    await help_cmd.finish(HELP_TEXT)
