"""静态数据表与文案常量。

本模块的内容本身不依赖 NoneBot 运行时，但通过 `import tsugu.constants` 访问它时
会先执行 `tsugu/__init__.py`，那里会调用 `get_plugin_config()`。因此探针脚本必须先
`nonebot.init()` 再 import，否则抛 `NoneBot has not been initialized`。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tsugu_api_core._typing import ServerId, _DifficultyId

# ---- 服务器 ----

# 服务器 ID 就是 0-4。用库里声明的 ServerId 而不是裸 int：tsugu_api_async 的
# 各接口都要求 ServerId，在源头标对，下游就不用到处 cast。
SERVER_ID_TO_NAME: dict[ServerId, str] = {
    0: "日服",
    1: "国际服",
    2: "台服",
    3: "国服",
    4: "韩服",
}

# 服务器名 -> ID。包括英文代号、中文全名和数字字符串。
SERVER_NAME_TO_ID: dict[str, ServerId] = {
    "jp": 0,
    "日服": 0,
    "en": 1,
    "国际服": 1,
    "tw": 2,
    "台服": 2,
    "cn": 3,
    "国服": 3,
    "kr": 4,
    "韩服": 4,
    "0": 0,
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
}

# ---- 档线 ----

TIER_LISTS: dict[str, list[int]] = {
    "jp": [
        20,
        30,
        40,
        50,
        100,
        200,
        300,
        400,
        500,
        1000,
        2000,
        5000,
        10000,
        20000,
        30000,
        50000,
    ],
    "tw": [100, 500],
    "en": [50, 100, 300, 500, 1000, 2000, 2500],
    "kr": [100],
    "cn": [
        20,
        30,
        40,
        50,
        100,
        200,
        300,
        400,
        500,
        1000,
        1500,
        2000,
        3000,
        4000,
        5000,
        10000,
        20000,
        30000,
        50000,
    ],
}


def tier_list_text() -> str:
    """拼接各服务器可用档线，用于 ycx 系列命令的帮助文本。"""
    return "\n".join(
        f"{server} : " + ", ".join(str(tier) for tier in tiers)
        for server, tiers in TIER_LISTS.items()
    )


# ---- 难度 ----

DIFFICULTY_NAMES: dict[str, _DifficultyId] = {
    "ez": 0,
    "easy": 0,
    "简单": 0,
    "nm": 1,
    "normal": 1,
    "普通": 1,
    "hd": 2,
    "hard": 2,
    "困难": 2,
    "ex": 3,
    "expert": 3,
    "专家": 3,
    "sp": 4,
    "special": 4,
    "特殊": 4,
}

DEFAULT_DIFFICULTY_ID: _DifficultyId = 3
"""查谱面未指定难度时使用 expert。"""

# ---- 车牌关键词 ----

CAR_KEYWORDS: list[str] = [
    "q1",
    "q2",
    "q3",
    "q4",
    "缺1",
    "缺2",
    "缺3",
    "缺4",
    "差1",
    "差2",
    "差3",
    "差4",
    "3火",
    "三火",
    "3把",
    "三把",
    "打满",
    "清火",
    "奇迹",
    "中途",
    "大e",
    "大分e",
    "exi",
    "大分跳",
    "大跳",
    "大a",
    "大s",
    "大分a",
    "大分s",
    "长途",
    "e3",
    "e长",
    "s3",
    "s长",
    "5级",
    "满级",
    "130",
    "150",
    "生日车",
    "军训",
    "禁fc",
]

FAKE_KEYWORDS: list[str] = [
    "🦐",
    "虾",
    "melt",
    "孜然",
    "孑然妒火",
    "周回",
    "实效",
    "删语音",
    "114514",
    "野兽",
    "恶臭",
    "1919",
    "下北泽",
    "粪",
    "糞",
    "臭",
    "11451",
    "xiabeize",
    "雀魂",
    "麻将",
    "打牌",
    "maj",
    "麻",
    "[",
    "]",
    "断幺",
    "qq.com",
    "腾讯会议",
    "master",
    "疯狂星期四",
    "离开了我们",
    "日元",
    "av",
    "bv",
]

# ---- 错误文案 ----

ERR_INCOMPLETE_CMD = "错误: 指令不完整"
ERR_SERVER_NOT_FOUND = "错误: 服务器名未能匹配任何服务器"
ERR_DIFFICULTY_NOT_FOUND = "错误: 难度名未能匹配任何难度"
ERR_PLAYER_ID_INVALID = "错误: 无效的玩家id"
ERR_BIND_TIMEOUT = "错误: 等待超时"
ERR_INDEX_INVALID = "错误: 无效的绑定信息ID"
ERR_NOT_BOUND_ANY = "未绑定任何玩家"
ERR_NOT_BOUND = "用户未绑定player"
ERR_NOT_BOUND_ON_SERVER = "用户在对应服务器上未绑定player"
ERR_GROUP_ONLY = "该指令仅在群聊中可用"
ERR_GACHA_DISABLED = "抽卡功能已关闭"
ERR_COMMAND_FAILED = "执行指令 {head} 失败"

HTTP_ERROR_TEXTS: dict[int, str] = {
    400: "错误: 请求参数错误, 可能因为版本与后端服务器版本不一致",
    404: "无法连接至后端服务器",
    500: "内部错误",
}
"""按 HTTP 状态码兜底的中文提示；未列出的状态码回退到后端返回的 data。"""

ERR_NETWORK = "错误: 后端服务器连接出错"


def incomplete_cmd_text(head: str) -> str:
    """参数不完整时的标准两行提示，与 mainline Tsugu 一致。"""
    return f"{ERR_INCOMPLETE_CMD}\n使用以下指令以查看帮助:\n  help {head}"


def command_failed_text(head: str) -> str:
    """处理器抛出未预期异常时的兜底提示，与 mainline Tsugu 一致。"""
    return ERR_COMMAND_FAILED.format(head=head)


# ---- 命令头表 ----

COMMAND_HEADS: list[tuple[str, str]] = [
    # (命令头, 命令ID)
    ("查卡", "search_card"),
    ("查卡牌", "search_card"),
    ("查卡面", "card_illustration"),
    ("查卡插画", "card_illustration"),
    ("查插画", "card_illustration"),
    ("查角色", "search_character"),
    ("查活动", "search_event"),
    ("查卡池", "search_gacha"),
    ("查曲", "search_song"),
    ("查谱面", "song_chart"),
    ("随机曲", "song_random"),
    ("随机", "song_random"),
    ("查询分数表", "song_meta"),
    ("查分数表", "song_meta"),
    ("查询分数榜", "song_meta"),
    ("查分数榜", "song_meta"),
    ("查试炼", "event_stage"),
    ("查stage", "event_stage"),
    ("查舞台", "event_stage"),
    ("查festival", "event_stage"),
    ("查5v5", "event_stage"),
    ("查玩家", "search_player"),
    ("查询玩家", "search_player"),
    ("抽卡模拟", "gacha_simulate"),
    ("抽卡", "gacha_switch"),
    ("开启抽卡", "gacha_on"),
    ("关闭抽卡", "gacha_off"),
    ("ycx", "cutoff"),
    ("ycxall", "cutoff_all"),
    ("myycx", "cutoff_all"),
    ("lsycx", "cutoff_history"),
    ("ycm", "ycm"),
    ("有车吗", "ycm"),
    ("车来", "ycm"),
    ("绑定玩家", "bind_player"),
    ("解除绑定", "unbind_player"),
    ("解绑玩家", "unbind_player"),
    ("主服务器", "main_server"),
    ("服务器模式", "main_server"),
    ("切换服务器", "main_server"),
    ("设置显示服务器", "display_servers"),
    ("默认服务器", "display_servers"),
    ("设置默认服务器", "display_servers"),
    ("玩家状态", "player_status"),
    ("玩家状态列表", "player_list"),
    ("玩家列表", "player_list"),
    ("玩家信息列表", "player_list"),
    ("玩家默认ID", "player_index"),
    ("默认玩家ID", "player_index"),
    ("默认玩家", "player_index"),
    ("玩家ID", "player_index"),
    ("开启车牌转发", "open_forward"),
    ("关闭车牌转发", "close_forward"),
    ("help", "help"),
    ("帮助", "help"),
]

ALIAS_FIELDS: dict[str, str] = {
    # 配置字段名 -> 命令 ID
    # 用户在 .env 里为某个命令追加的别名，分派器会把它们并进命令头表。
    # 这张映射是必须的：配置字段名与命令 ID 对不上的有 7 处
    # （switch_index/player_index、default_servers/display_servers、
    #  ycx/cutoff、ycx_all/cutoff_all、lsycx/cutoff_history），
    # 靠改名字推导会漏掉它们。
    "tsugu_open_forward_aliases": "open_forward",
    "tsugu_close_forward_aliases": "close_forward",
    "tsugu_bind_player_aliases": "bind_player",
    "tsugu_unbind_player_aliases": "unbind_player",
    "tsugu_main_server_aliases": "main_server",
    "tsugu_default_servers_aliases": "display_servers",
    "tsugu_player_status_aliases": "player_status",
    "tsugu_player_list_aliases": "player_list",
    "tsugu_switch_index_aliases": "player_index",
    "tsugu_ycm_aliases": "ycm",
    "tsugu_search_player_aliases": "search_player",
    "tsugu_search_card_aliases": "search_card",
    "tsugu_card_illustration_aliases": "card_illustration",
    "tsugu_search_character_aliases": "search_character",
    "tsugu_search_event_aliases": "search_event",
    "tsugu_search_song_aliases": "search_song",
    "tsugu_song_chart_aliases": "song_chart",
    "tsugu_song_random_aliases": "song_random",
    "tsugu_song_meta_aliases": "song_meta",
    "tsugu_event_stage_aliases": "event_stage",
    "tsugu_search_gacha_aliases": "search_gacha",
    "tsugu_ycx_aliases": "cutoff",
    "tsugu_ycx_all_aliases": "cutoff_all",
    "tsugu_lsycx_aliases": "cutoff_history",
    "tsugu_gacha_simulate_aliases": "gacha_simulate",
}
"""25 个可配置别名字段与命令 ID 的对应关系。

`gacha_switch` / `gacha_on` / `gacha_off` / `help` 没有对应的别名字段，
别名表里也查不到，属正常。
"""
