"""静态数据表与文案常量。此模块不依赖 NoneBot 运行时，可被探针脚本直接 import。"""

from __future__ import annotations

# ---- 服务器 ----

SERVER_ID_TO_NAME: dict[int, str] = {
    0: "日服",
    1: "国际服",
    2: "台服",
    3: "国服",
    4: "韩服",
}

# 服务器名 -> ID。包括英文代号、中文全名和数字字符串。
SERVER_NAME_TO_ID: dict[str, int] = {
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

DIFFICULTY_NAMES: dict[str, int] = {
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

DEFAULT_DIFFICULTY_ID = 3
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
    "生日车",
    "军训",
    "禁fc",
]

FAKE_KEYWORDS: list[str] = [
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
