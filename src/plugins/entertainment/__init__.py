import random

from nonebot import get_plugin_config, on_command
from nonebot.adapters.qq import MessageEvent
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="entertainment",
    description="娱乐功能插件",
    usage="发送 /random, /joke, /dice 等命令",
    config=Config,
)

config = get_plugin_config(Config)

# 随机数命令
random_cmd = on_command("random", priority=10, block=True)


@random_cmd.handle()
async def handle_random(event: MessageEvent, args: MessageEvent = CommandArg()):
    args_str = args.extract_plain_text().strip()
    if not args_str:
        await random_cmd.finish("请提供范围，例如：/random 1 100")

    try:
        parts = args_str.split()
        if len(parts) != 2:
            await random_cmd.finish("格式错误，请使用：/random <最小值> <最大值>")

        min_val = int(parts[0])
        max_val = int(parts[1])

        if min_val >= max_val:
            await random_cmd.finish("最小值必须小于最大值")

        result = random.randint(min_val, max_val)
        await random_cmd.finish(f"随机数结果：{result}")

    except ValueError:
        await random_cmd.finish("请输入有效的数字")


# 笑话命令
joke_cmd = on_command("joke", aliases={"笑话"}, priority=10, block=True)

JOKES = [
    "为什么程序员总是分不清万圣节和圣诞节？\n因为 Oct 31 == Dec 25。",
    "什么动物最容易摔倒？\n狐狸，因为它很狡猾（脚滑）。",
    "为什么数学书很悲伤？\n因为它有太多问题。",
    "什么鱼不能吃？\n木鱼。",
    "什么门永远关不上？\n球门。",
    "什么水不能喝？\n薪水。",
    "什么路最窄？\n冤家路窄。",
    "什么官不发工资，却要给别人钱？\n新郎官。",
]


@joke_cmd.handle()
async def handle_joke(event: MessageEvent):
    joke = random.choice(JOKES)
    await joke_cmd.finish(joke)


# 掷骰子命令
dice_cmd = on_command("dice", aliases={"骰子"}, priority=10, block=True)

DICE_FACES = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]


@dice_cmd.handle()
async def handle_dice(event: MessageEvent):
    result = random.randint(1, 6)
    dice_face = DICE_FACES[result - 1]
    await dice_cmd.finish(f"骰子结果：{dice_face} ({result}点)")
