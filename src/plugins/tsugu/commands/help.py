"""帮助命令与帮助文本。

USAGES 是帮助文本的唯一来源：命令的详细用法从这里读，help 总表的
一句话说明取每个条目的第二行。改命令时只改这里。
"""

from __future__ import annotations

from .. import constants as const
from . import Ctx, register

USAGES: dict[str, str] = {
    "help": """help [命令名]
显示全部命令，或查看某条命令的详细用法
示例:
    help
    help 查卡""",
    "search_card": """查卡 <关键词...>
根据关键词或卡牌ID查询卡片信息，请使用空格隔开所有参数
示例:
    查卡 1399 :返回1399号卡牌的信息
    查卡 绿 tsugu :返回所有属性为pure的羽泽鸫的卡牌列表""",
    "card_illustration": """查卡面 <卡牌ID>
根据卡牌ID查询卡片插画
示例:
    查卡面 1399 :返回1399号卡牌的插画""",
    "search_character": """查角色 <关键词...>
根据关键词或角色ID查询角色信息
示例:
    查角色 10 :返回10号角色的信息
    查角色 吉他 :返回所有角色模糊搜索标签中包含吉他的角色列表""",
    "search_event": """查活动 <关键词...>
根据关键词或活动ID查询活动信息
示例:
    查活动 177 :返回177号活动的信息
    查活动 绿 tsugu :返回所有属性加成为pure，且活动加成角色中包括羽泽鸫的活动列表""",
    "search_gacha": """查卡池 <卡池ID>
根据卡池ID查询卡池信息
示例:
    查卡池 922""",
    "search_song": """查曲 <关键词...>
根据关键词或曲目ID查询曲目信息
示例:
    查曲 1 :返回1号曲的信息
    查曲 ag lv27 :返回所有难度为27的ag曲列表""",
    "song_chart": """查谱面 <曲目ID> [难度]
根据曲目ID与难度查询谱面信息，难度缺省为 expert
示例:
    查谱面 1 :返回1号曲的expert谱面
    查谱面 1 special :返回1号曲的special难度谱面""",
    "song_random": """随机曲 [关键词...]
随机返回一首符合条件的曲目，不带参数则全曲随机
示例:
    随机曲 :全曲随机
    随机曲 lv24 ag :在所有包含24等级难度的afterglow曲中随机""",
    "song_meta": """查询分数表 [服务器]
查询指定服务器的歌曲分数表，缺省为用户的主服务器
示例:
    查询分数表 cn :返回国服的歌曲分数表""",
    "event_stage": """查试炼 [活动ID] [-m]
查询指定活动的试炼信息，缺省为当前活动；-m 附带歌曲 meta
示例:
    查试炼 :返回当前活动的试炼信息
    查试炼 157 -m :返回157号活动的试炼信息，包含歌曲meta""",
    "search_player": """查玩家 <玩家ID> [服务器]
查询指定ID玩家的信息，缺省从主服务器查询
示例:
    查玩家 10000000 :查询主服务器中玩家ID为10000000的玩家
    查玩家 40474621 jp :查询日服玩家ID为40474621的玩家""",
    "gacha_simulate": """抽卡模拟 <次数> [卡池ID]
模拟抽卡，卡池ID缺省为当前卡池
示例:
    抽卡模拟 10 :模拟抽卡10次
    抽卡模拟 300 922 :模拟抽卡300次，卡池为922号卡池""",
    "cutoff": f"""ycx <档位> [活动ID] [服务器]
查询指定档位的预测线，缺省为当前活动与主服务器
可用档线:
{const.tier_list_text()}
示例:
    ycx 1000 :返回主服务器当前活动1000档位的档线与预测线
    ycx 1000 177 jp :返回日服177号活动1000档位的档线与预测线""",
    "cutoff_all": """ycxall [活动ID] [服务器]
查询所有档位的预测线，缺省为当前活动与主服务器
示例:
    ycxall :返回主服务器当前活动的全部档位预测线""",
    "cutoff_history": """lsycx <档位> [活动ID] [服务器]
查询指定档位以及最近4期同类型活动的历史档线，缺省为当前活动与主服务器
示例:
    lsycx 1000 :返回主服务器当前活动1000档位与最近4期同类型活动的档线""",
    "ycm": """ycm [关键词...]
获取全部车牌，可用关键词过滤
示例:
    ycm :获取全部车牌
    ycm 大分 :获取备注中包含「大分」的车牌""",
    "bind_player": """绑定玩家 [服务器]
开始玩家数据绑定流程，请不要在指令后直接添加玩家ID
获得临时验证数字后，把游戏签名或卡组名改成该数字，再回复你的玩家ID
示例:
    绑定玩家 :绑定到主服务器
    绑定玩家 jp :绑定日服账号""",
    "unbind_player": """解除绑定 [服务器]
解除指定服务器的玩家绑定，缺省为主服务器
示例:
    解除绑定 :解除主服务器的绑定""",
    "main_server": """主服务器 <服务器>
将指定服务器设为主服务器
示例:
    主服务器 cn :将国服设为主服务器""",
    "display_servers": """设置显示服务器 <服务器...>
用空格分隔服务器列表，设置信息展示时的默认服务器顺序
示例:
    设置默认服务器 国服 日服""",
    "player_status": """玩家状态 [序号] [服务器]
查询已绑定玩家的状态，序号或服务器最多给一个
示例:
    玩家状态 :查询主服务器上的默认玩家
    玩家状态 2 :查询第2条绑定
    玩家状态 jp :查询日服上的绑定""",
    "player_list": """玩家状态列表
列出全部已绑定的玩家与当前的默认设置""",
    "player_index": """玩家默认ID <序号>
设置默认展示的玩家绑定序号
示例:
    玩家默认ID 2""",
    "open_forward": """开启车牌转发
开启后，包含车牌关键词的消息会自动上传到车站""",
    "close_forward": """关闭车牌转发
关闭车牌自动上传""",
    "gacha_switch": """抽卡 <on|off|开启|关闭>
开关本群的抽卡功能，仅群聊可用
示例:
    开启抽卡
    关闭抽卡""",
    "gacha_on": """开启抽卡
开启本群的抽卡功能，仅群聊可用""",
    "gacha_off": """关闭抽卡
关闭本群的抽卡功能，仅群聊可用""",
}

HELP_ORDER: list[str] = [
    "search_card",
    "card_illustration",
    "search_character",
    "search_event",
    "search_gacha",
    "search_song",
    "song_chart",
    "song_random",
    "song_meta",
    "event_stage",
    "search_player",
    "gacha_simulate",
    "cutoff",
    "cutoff_all",
    "cutoff_history",
    "ycm",
    "bind_player",
    "unbind_player",
    "main_server",
    "display_servers",
    "player_status",
    "player_list",
    "player_index",
    "open_forward",
    "close_forward",
    "gacha_switch",
    "gacha_on",
    "gacha_off",
    "help",
]


def heads_of(command: str) -> list[str]:
    """某个命令 ID 对应的全部命令头。"""
    return [head for head, cmd in const.COMMAND_HEADS if cmd == command]


@register("help")
async def handle_help(ctx: Ctx) -> None:
    if ctx.args:
        query = ctx.args[0]
        for command, usage in USAGES.items():
            if query == command or query in heads_of(command):
                await ctx.reply_text(usage)
                return
        await ctx.reply_text(f"未找到命令 {query}")
        return

    lines = ["未知命令，可用命令如下：", ""]
    for command in HELP_ORDER:
        heads = heads_of(command)
        usage = USAGES.get(command)
        if not heads or usage is None:
            continue
        summary = usage.splitlines()[1]
        lines.append(" / ".join(heads))
        lines.append(f"    {summary}")
    await ctx.reply_text("\n".join(lines))
