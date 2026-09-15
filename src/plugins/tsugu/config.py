"""Tsugu 插件配置。字段名与 nonebot-plugin-tsugu-bangdream-bot 保持一致。"""

from __future__ import annotations

from pydantic import BaseModel


class Config(BaseModel):
    """Tsugu 插件配置。"""

    tsugu_backend_url: str = "http://tsugubot.com:8080"
    """查询后端地址。"""

    tsugu_data_backend_url: str = "http://tsugubot.com:8080"
    """用户数据与车站后端地址。"""

    tsugu_platform: str = "red"
    """用户数据使用的平台标识，red 与官方 Tsugu QQ Bot 互通。"""

    tsugu_use_easy_bg: bool = False
    """简易背景，开启大幅提速但界面简陋。"""

    tsugu_compress: bool = True
    """后端压缩图片，体积小、传输快。"""

    tsugu_no_space: bool = False
    """命令头后允许不跟空格。"""

    tsugu_at: bool = False
    """回复时 @ 用户。"""

    tsugu_timeout: float = 30.0
    """后端请求超时（秒）。"""

    tsugu_retries: int = 3
    """后端请求重试次数。"""

    tsugu_proxy: str = ""
    """代理地址，空串表示不使用。"""

    tsugu_backend_proxy: bool = False
    """查询后端是否走代理。"""

    tsugu_data_backend_proxy: bool = False
    """用户数据后端是否走代理。"""

    tsugu_max_messages: int = 5
    """单次回复最多发送几条被动消息，QQ 官方上限为 5。"""

    tsugu_bind_timeout: int = 300
    """绑定流程等待用户回复的秒数。"""

    tsugu_bandori_station_token: str | None = None
    """BandoriStation 令牌，None 时用 Tsugu 后端配置的公共令牌。"""

    # ---- 命令别名扩充，与 nonebot-tsugu 同名同义 ----
    tsugu_open_forward_aliases: set[str] = set()
    tsugu_close_forward_aliases: set[str] = set()
    tsugu_bind_player_aliases: set[str] = set()
    tsugu_unbind_player_aliases: set[str] = set()
    tsugu_main_server_aliases: set[str] = set()
    tsugu_default_servers_aliases: set[str] = set()
    tsugu_player_status_aliases: set[str] = set()
    tsugu_player_list_aliases: set[str] = set()
    tsugu_switch_index_aliases: set[str] = set()
    tsugu_ycm_aliases: set[str] = set()
    tsugu_search_player_aliases: set[str] = set()
    tsugu_search_card_aliases: set[str] = set()
    tsugu_card_illustration_aliases: set[str] = set()
    tsugu_search_character_aliases: set[str] = set()
    tsugu_search_event_aliases: set[str] = set()
    tsugu_search_song_aliases: set[str] = set()
    tsugu_song_chart_aliases: set[str] = set()
    tsugu_song_random_aliases: set[str] = set()
    tsugu_song_meta_aliases: set[str] = set()
    tsugu_event_stage_aliases: set[str] = set()
    tsugu_search_gacha_aliases: set[str] = set()
    tsugu_ycx_aliases: set[str] = set()
    tsugu_ycx_all_aliases: set[str] = set()
    tsugu_lsycx_aliases: set[str] = set()
    tsugu_gacha_simulate_aliases: set[str] = set()
