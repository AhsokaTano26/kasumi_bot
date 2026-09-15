# Tsugu QQ 官方 Bot 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `kasumi_bot` 从演示性插件集合改造成 Tsugu BanGDream Bot 的 QQ 官方 Bot 前端，命令集与 mainline Tsugu 一致。

**Architecture:** 单个 NoneBot2 插件 `src/plugins/tsugu/`，自建触发层替代 `on_command`（QQ 群里的 `@bot` 会让 `message[0]` 变成 `MentionUser`，`TrieRule` 直接放弃匹配）。数据查询与图片渲染全部委托给 Tsugu 公共后端；用户数据存在 Tsugu 后端（`platform="red"`），群级设置存本地 SQLite。

**Tech Stack:** Python 3.9+、NoneBot2 2.5、nonebot-adapter-qq 1.7、tsugu-api-python 1.5.10、SQLAlchemy（经 nonebot-plugin-orm 0.8）、Pydantic v2、Ruff、Pyright。

**设计规格：** `docs/superpowers/specs/2026-09-15-tsugu-qq-bot-design.md`（实现过程中如遇规格未覆盖的细节，以规格的原则为准，并把决定补回规格）。

## Global Constraints

- **Python 版本**：`requires-python = ">=3.10, <4.0"`，ruff `target-version = "py310"`，pyright `pythonVersion = "3.10"`。
  这个下限是实测出来的，不是随意选的：`nonebot2` 2.5.0 声明 `>=3.10, <4.0`、`nonebot-adapter-qq` 1.7.1 声明 `>=3.10, <4`、
  `websockets` 16.0 声明 `>=3.10`，所以 3.9 根本无法安装这套依赖。Task 1 已把三处声明改到 3.10。
- **类型注解风格**：用现代写法——内置泛型小写（`list[X]`、`dict[K, V]`、`set[X]`、`tuple[X, ...]`）、
  联合类型用 `X | None` / `X | Y`、抽象类型从 `collections.abc` 导入（`Iterable`、`Sequence`、`Awaitable`、`Callable`）。
  每个文件顶部写 `from __future__ import annotations`。
  这不是风格偏好而是硬约束：`pyproject.toml` 的 ruff 选择集包含 `UP`，且 `target-version = "py310"`，
  所以 `List[X]` / `Optional[X]` / `from typing import Dict` 会直接让 `ruff check src/` 报错（UP006/UP035/UP045）。
  `[tool.ruff.lint.pyupgrade] keep-runtime-typing = true` **不会**抑制这三条规则（ruff 0.15.13 实测，true/false 输出完全一致）。
  从 `typing` 只导入 `Any`、`TYPE_CHECKING` 这类真正还需要的东西。
- **代码风格**：ruff `line-length = 88`、LF 行尾。提交前必须 `ruff check src/` 与 `ruff format src/` 均无输出。
- **类型检查**：`pyright src/` 必须 0 error。直接运行即可，不需要加 `--pythonpath`——Task 2 已在
  `[tool.pyright]` 里补上 `venvPath` / `venv` 两个设置（实测：不加时 pyright 解析不出 `.venv` 里的
  `nonebot`、`pydantic`、`tsugu_api_async`，会报 4 条 `reportMissingImports`）。
- **导入风格**：跨子包用绝对导入（`from tsugu import api` / `from tsugu import constants as const`），
  同包内用单点相对导入（`from . import Ctx, register`）。**不要用父级相对导入 `from .. import x`**——
  ruff 的 `TID252` 会报错。常量模块的别名用小写 `const`，不要用 `K`（`N812` 禁止小写模块用大写别名）。
- **布尔参数**：一律写成仅关键字参数（`*, enabled: bool`），调用时用 `enabled=True`（`FBT001`/`FBT003`）。
- **`except Exception`**：**一律要加 `# noqa: BLE001`**。实测（ruff 0.15.13 + 本项目配置）即使写成
  `except Exception as exc:` 并在体内使用 `exc`，BLE001 依然触发，所以这条 noqa 是必需的，不是可选的。
  注意配套约束：`as exc` 而体内不用 `exc` 会触发 `F841`，所以要么用上 `exc`（例如
  `logger.opt(exception=exc)`），要么写成不带 `as` 的 `except Exception:  # noqa: BLE001`。
- **提交信息**：**只能一句话**，形如 `feat: 新增触发层`。不留正文、不留空行、**绝不加 `Co-Authored-By` 或任何 Claude 字样**。
- **不写 pytest 测试套件**（用户明确要求精简）。每个任务的验证用一次性探针脚本或真实后端调用完成。探针脚本写到 `$CLAUDE_JOB_DIR/tmp/`（该变量未设置时用 `/tmp`），**不要提交到仓库**。
  探针脚本的固定前缀：`sys.path.insert(0, "src/plugins")` 之后必须紧跟 `import nonebot` + `nonebot.init()`，**然后**才能 import `tsugu.*`。
  原因：`tsugu/__init__.py` 在 import 时就会调用 `get_plugin_config()`，未初始化 NoneBot 时直接抛 `NoneBot has not been initialized`。
  直接 import 包即可，不需要 `nonebot.load_plugin()`——探针不跑 bot 事件循环。
- **用户数据平台标识**：固定 `"red"`，通过 `TSUGU_PLATFORM` 可改。
- **配置项命名**：全部 `TSUGU_` 前缀，字段名与 `nonebot-plugin-tsugu-bangdream-bot` 保持一致。
- **`nonebot2[websockets]` 必须保留**：QQ 适配器连接 QQ 网关依赖它提供的 `WebSocketClientMixin` 驱动，没有它适配器启动即抛异常。
- **错误文案**：用户可见的提示一律用中文，格式与 mainline Tsugu 一致（见规格第 8 节）。

## 关键事实（已实测，实现时直接依赖，不要重新验证）

1. `bot.send(event, msg)` 自动填 `msg_id=event.id`，并对同一事件内每次发送自增 `event._reply_seq` 作为 `msg_seq`。**不要自己维护 `msg_seq`**。
2. `event.get_message().extract_plain_text()` 会剥掉 `@bot`，但保留前导空格，必须 `.strip()`。
3. `MessageSegment.file_image(data: bytes)` 产生 `file_type=1` 的 `LocalAttachment`，即图片。上传路径**不取决于是否传 `file_name`**：`_extract_qq_media` 只在 `file_data` 超过 10MB 时才往 kwargs 塞 `file_name`，`send_to_group` 再按该键是否存在在 `post_group_upload`（分块）与 `post_group_files`（普通）之间二选一。所以约 310KB 的图片两条路都会走普通上传；反之 ≥10MB 的图片会自动走分块上传，模块层无法干预。
4. `tsugu_api_core` 的异常分类：HTTP 200 正常返回；400 → `BadRequestError`；404/409/422/500 → `FailedException`（有 `.status_code` 和 `.data`）；其他 → `HTTPStatusError`。网络/超时异常直接向上抛。
5. `tsugu_api_async.settings` 的 `use_easy_bg` 与 `compress` 是**全局设置**，由库自动注入每次请求，业务代码不需要逐次传参。
6. 公共后端 `tsugubot.com:8080` 的 `/user/*` 与 `/station/*` 均已挂载（实测 `getUserData` 空 body 返回 400 参数错误而非 404）。
7. `nonebot_plugin_orm` 在 `ALEMBIC_STARTUP_CHECK=False` 时，启动会跑 `migrate.sync revision`，从模型自动生成并应用迁移，**不需要手写迁移脚本**。

## 文件结构

| 文件 | 职责 |
|---|---|
| `src/plugins/tsugu/__init__.py` | 插件入口：PluginMetadata、把配置写进 `tsugu_api_async.settings`、唯一的 `on_message` 分派器、绑定流程的待处理状态 |
| `src/plugins/tsugu/config.py` | Pydantic `Config` 模型 |
| `src/plugins/tsugu/constants.py` | 服务器表、档位表、难度关键词、车牌关键词、错误文案、命令头表 |
| `src/plugins/tsugu/rule.py` | 触发层：命令头匹配、shortcut 正则、车牌正则、QQ 事件小工具 |
| `src/plugins/tsugu/sender.py` | 后端响应 → QQ 消息的拆分、截断与发送 |
| `src/plugins/tsugu/api.py` | `tsugu_api_async` 封装 + 异常到中文文案的映射 + 服务器/难度名解析 |
| `src/plugins/tsugu/user.py` | 用户数据读写、玩家选择、绑定/解绑流程的纯逻辑 |
| `src/plugins/tsugu/db.py` | ORM 模型 `GroupSetting` 与群级设置读写 |
| `src/plugins/tsugu/commands/__init__.py` | 汇总 `HANDLERS` 分派表 |
| `src/plugins/tsugu/commands/card.py` | 查卡、查卡面 |
| `src/plugins/tsugu/commands/character.py` | 查角色 |
| `src/plugins/tsugu/commands/song.py` | 查曲、查谱面、随机曲、查询分数表 |
| `src/plugins/tsugu/commands/event.py` | 查活动、查试炼 |
| `src/plugins/tsugu/commands/cutoff.py` | ycx、ycxall、lsycx |
| `src/plugins/tsugu/commands/gacha.py` | 查卡池、抽卡模拟、抽卡开关 |
| `src/plugins/tsugu/commands/player.py` | 查玩家 |
| `src/plugins/tsugu/commands/station.py` | ycm |
| `src/plugins/tsugu/commands/settings.py` | 绑定/解绑/主服务器/显示服务器/玩家状态/玩家默认ID/车牌转发 |
| `src/plugins/tsugu/commands/help.py` | help / 帮助 |

**为什么把纯逻辑和 NoneBot 粘合分开**：`rule.py` 的解析函数、`sender.py` 的 `split_messages`、`user.py` 的文本构造函数都不碰 NoneBot 运行时，可以直接在探针脚本里 import 并断言。这是本项目唯一能低成本验证的部分，务必保持这些函数纯净。

---

### Task 1: 清场与依赖基线

拆掉旧的演示性插件，把依赖和驱动配置修到能跑 Tsugu 插件的状态。

**Files:**
- Delete: `src/plugins/bangdream/`、`src/plugins/live/`、`src/plugins/proactive/`、`src/plugins/basic/`、`src/plugins/test/`
- Delete: `data/db.sqlite3`、`data/nonebot_plugin_orm/`
- Modify: `pyproject.toml`（`[project] dependencies`）
- Modify: `.env`
- Modify: `requirements.txt`（重新生成）

**Interfaces:**
- Consumes: 无
- Produces: 一个能启动、零插件、驱动具备 WebSocket 客户端能力的 NoneBot 工程

- [ ] **Step 1: 删除旧插件与旧数据**

```bash
cd /Users/tano/Documents/GitHub/personal/kasumi_bot
git rm -r src/plugins/bangdream src/plugins/live src/plugins/proactive src/plugins/basic src/plugins/test
rm -rf data
```

- [ ] **Step 2: 改 pyproject.toml 的依赖**

把 `[project]` 的 `dependencies` 整段替换为：

```toml
dependencies = [
    "nonebot2[fastapi]>=2.5.0",
    "nonebot2[httpx]>=2.5.0",
    "nonebot2[websockets]>=2.5.0",
    "nonebot-adapter-qq>=1.7.0",
    "nonebot-plugin-orm[sqlite]>=0.8.0",
    "tsugu-api-python[httpx]>=1.5.10"
]
```

改动要点：去掉 `nonebot-plugin-apscheduler`（旧 `live` 插件的定时爬取）；新增 `tsugu-api-python`；`nonebot2[websockets]` 保留（QQ 适配器需要）。

- [ ] **Step 3: 修 .env 的驱动**

把 `.env` 整个文件替换为：

```
ENVIRONMENT=dev
DRIVER=~fastapi+~httpx+~websockets
LOCALSTORE_USE_CWD=true
SQLALCHEMY_DATABASE_URL=sqlite+aiosqlite:///data/db.sqlite3
ALEMBIC_STARTUP_CHECK=False
```

`DRIVER` 是关键：原来的 `~fastapi+~httpx` 解析出的 `CombinedDriver` 不满足 `WebSocketClientMixin`，QQ 适配器会在 `adapter.py:74-80` 直接抛 `QQ Adapter need a WebSocketClient Driver to work.`

- [ ] **Step 4: 安装并重新生成 requirements.txt**

```bash
cd /Users/tano/Documents/GitHub/personal/kasumi_bot
.venv/bin/pip install -q -e ".[dev]"
.venv/bin/pip freeze --exclude-editable > requirements.txt
grep -iE "^-e|file://" requirements.txt && echo "!! 混入了本地路径" || echo "requirements.txt 干净"
```

`--exclude-editable` 是必须的：这个 venv 里本项目是以可编辑模式装的，`pip freeze` 会输出
`-e git+ssh://git@github.com/.../kasumi_bot.git@<sha>#egg=kasumi_bot`。而 `Dockerfile` 执行的是
`pip wheel --requirement ./requirements.txt`，构建容器没有 SSH key，那一行会让整个镜像构建失败。

- [ ] **Step 5: 建立可移植的启动探针**

macOS 没有 GNU `timeout`（`command -v timeout` 与 `gtimeout` 都为空），所以不能用
`timeout N nb run`。这个脚本在后续每个任务里复用。

写到 `$CLAUDE_JOB_DIR/tmp/boot_probe.py`（`$CLAUDE_JOB_DIR` 未设置时用 `/tmp`）：

```python
"""启动 Bot 指定秒数后杀掉，把日志写进文件。替代 macOS 上不存在的 GNU timeout。

用法: python boot_probe.py [秒数] [日志路径]
"""

import os
import signal
import subprocess
import sys

seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 20
log_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/nb_boot.log"

proc = subprocess.Popen(
    [".venv/bin/nb", "run"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    # 独立进程组，这样能连同它派生的子进程一起杀掉
    start_new_session=True,
)
try:
    output, _ = proc.communicate(timeout=seconds)
except subprocess.TimeoutExpired:
    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    output, _ = proc.communicate()

output = output or ""
with open(log_path, "w", encoding="utf-8") as handle:
    handle.write(output)

print(f"启动 {seconds}s 后已终止，日志写入 {log_path}（{len(output)} 字符）")
```

运行一次确认脚本本身可用（此时工程还是零插件状态，应当能正常启动）：

```bash
cd /Users/tano/Documents/GitHub/personal/kasumi_bot
.venv/bin/python "$CLAUDE_JOB_DIR/tmp/boot_probe.py" 15 "$CLAUDE_JOB_DIR/tmp/boot.log"
```

Expected: 打印 `启动 15s 后已终止，日志写入 ...`。

- [ ] **Step 6: 验证驱动具备 WebSocket 客户端能力**

```bash
.venv/bin/python -c "
import nonebot
from nonebot.drivers import WebSocketClientMixin, HTTPClientMixin
nonebot.init(driver='~fastapi+~httpx+~websockets', _env_file=None)
d = nonebot.get_driver()
assert isinstance(d, WebSocketClientMixin), 'WS 客户端能力缺失'
assert isinstance(d, HTTPClientMixin), 'HTTP 客户端能力缺失'
print('驱动 OK:', type(d).__name__)
"
```

Expected: 打印 `驱动 OK: CombinedDriver`，无 AssertionError。

- [ ] **Step 7: 验证工程能启动**

```bash
cd /Users/tano/Documents/GitHub/personal/kasumi_bot
.venv/bin/python "$CLAUDE_JOB_DIR/tmp/boot_probe.py" 15 "$CLAUDE_JOB_DIR/tmp/boot.log"
tail -20 "$CLAUDE_JOB_DIR/tmp/boot.log"
```

Expected: 日志里出现 `NoneBot is initializing...` 与 `Running on http://127.0.0.1:8080`，且**没有** `QQ Adapter need a WebSocketClient Driver` 报错，没有插件加载错误。进程被探针杀掉是预期的。

- [ ] **Step 8: 提交**

```bash
git add -A
git commit -m "refactor: 移除演示插件并补齐 QQ 适配器所需的驱动与依赖"
```

---

### Task 2: 配置与常量

建立插件的配置模型、静态数据表和插件骨架。骨架此时不含任何命令，只保证能被 NoneBot 加载、能加载 ORM 模型。

**Files:**
- Create: `src/plugins/tsugu/__init__.py`
- Create: `src/plugins/tsugu/config.py`
- Create: `src/plugins/tsugu/constants.py`

**Interfaces:**
- Consumes: Task 1 的依赖与环境
- Produces:
  - `config.Config`：Pydantic 模型，字段见下
  - `constants.SERVER_NAME_TO_ID: dict[str, int]`、`constants.SERVER_ID_TO_NAME: dict[int, str]`
  - `constants.TIER_LISTS: dict[str, list[int]]`
  - `constants.DIFFICULTY_NAMES: dict[str, int]`
  - `constants.CAR_KEYWORDS: list[str]`、`constants.FAKE_KEYWORDS: list[str]`
  - `constants.HTTP_ERROR_TEXTS: dict[int, str]`
  - `constants.ERR_*`：一组错误文案常量
  - `constants.COMMAND_HEADS: list[tuple[str, str]]`：`(命令头, 命令ID)` 列表，**任务 3 会消费它建查找表**

- [ ] **Step 1: 写 config.py**

```python
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
```

- [ ] **Step 2: 写 constants.py**

```python
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
```

`COMMAND_HEADS` 里 `抽卡` 与 `抽卡模拟`、`查卡` 与 `查卡面`/`查卡牌`/`查卡池`、`玩家状态` 与 `玩家状态列表` 都是前缀关系——**顺序无所谓**，任务 3 的查找表会按长度降序排列，长命令头永远先匹配。

mainline Tsugu 的关键词表里 `q1`-`q4` 有大小写两份，这里只保留小写：`rule.match_car` 会先把消息
`.lower()` 再匹配，大写条目永远不可达，留下就是死数据。

已核对 `CAR_KEYWORDS` 与 `FAKE_KEYWORDS` 之间没有任何互相包含的组合，所以「含车牌词且不含反词」
的判定不会自相矛盾。

- [ ] **Step 3: 写最小的 __init__.py**

此步只建立骨架，命令分派留到 Task 7。

```python
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
    supported_adapters={"~qq"},
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
```

- [ ] **Step 4: 验证配置默认值**

```bash
cd /Users/tano/Documents/GitHub/personal/kasumi_bot
.venv/bin/python -c "
import sys; sys.path.insert(0, 'src/plugins')
import nonebot; nonebot.init()
from tsugu.config import Config
c = Config()
assert c.tsugu_platform == 'red'
assert c.tsugu_backend_url == 'http://tsugubot.com:8080'
assert c.tsugu_compress is True
assert c.tsugu_max_messages == 5
assert c.tsugu_bind_timeout == 300
assert c.tsugu_bandori_station_token is None
assert c.tsugu_search_card_aliases == set()
print('Config 默认值 OK')
"
```

Expected: 打印 `Config 默认值 OK`。

- [ ] **Step 5: 验证常量表**

```bash
cd /Users/tano/Documents/GitHub/personal/kasumi_bot
.venv/bin/python -c "
import sys; sys.path.insert(0, 'src/plugins')
import nonebot; nonebot.init()
from tsugu import constants as K
assert K.SERVER_NAME_TO_ID['cn'] == 3
assert K.SERVER_NAME_TO_ID['国服'] == 3
assert K.SERVER_NAME_TO_ID['3'] == 3
assert K.SERVER_ID_TO_NAME[3] == '国服'
assert K.DIFFICULTY_NAMES['expert'] == 3
assert K.DEFAULT_DIFFICULTY_ID == 3
assert len(K.CAR_KEYWORDS) > 30
assert '114514' in K.FAKE_KEYWORDS
heads = [h for h, _ in K.COMMAND_HEADS]
assert len(heads) == len(set(heads)), '命令头有重复: ' + str([h for h in heads if heads.count(h) > 1])
ids = {i for _, i in K.COMMAND_HEADS}
assert 'search_card' in ids and 'gacha_switch' in ids and 'help' in ids
print('constants OK:', len(K.COMMAND_HEADS), '个命令头,', len(ids), '个命令')
"
```

Expected: 打印 `constants OK: 55 个命令头, 29 个命令`。这两个数字是硬性的：55 个命令头必须互不为重复键，29 个命令 ID 必须与 Task 10 的 `USAGES` 完全一致。

- [ ] **Step 6: 验证插件能被 NoneBot 加载**

```bash
cd /Users/tano/Documents/GitHub/personal/kasumi_bot
.venv/bin/python "$CLAUDE_JOB_DIR/tmp/boot_probe.py" 15 "$CLAUDE_JOB_DIR/tmp/boot.log"
tail -20 "$CLAUDE_JOB_DIR/tmp/boot.log"
```

Expected: 日志里出现 `Succeeded to load plugin "tsugu" from "src.plugins.tsugu"`，无报错。

- [ ] **Step 7: 静态检查并提交**

```bash
.venv/bin/ruff check src/ && .venv/bin/ruff format src/ && .venv/bin/pyright src/
git add -A
git commit -m "feat: 新增 Tsugu 插件骨架、配置模型与常量表"
```

---

### Task 3: 触发层解析

本项目最容易出错的一环。全部是纯函数，不依赖 NoneBot 运行时，可以脱离框架验证。

**Files:**
- Create: `src/plugins/tsugu/rule.py`

**Interfaces:**
- Consumes: `constants.COMMAND_HEADS`
- Produces:
  - `rule.Match`：frozen dataclass，字段 `command: str`、`head: str`、`args: list[str]`
  - `rule.build_head_table(heads) -> dict[str, str]`
  - `rule.match_command(text, table, *, no_space=False) -> Match | None`
  - `rule.apply_shortcut(text) -> str`
  - `rule.match_car(text, car_keywords, fake_keywords) -> tuple[int, str] | None`
  - `rule.normalize(text) -> str`
  - `rule.get_group_openid(event) -> str | None`

- [ ] **Step 1: 写 rule.py**

```python
"""QQ 官方 Bot 触发层。

QQ 群里 Bot 只能收到 @ 了它的消息，而 @ 会被适配器解析成 MentionUser 段。
nonebot 的 TrieRule.get_value 只看 message[0]，遇到非文本段直接放弃匹配，
所以标准的 on_command 在群里完全失效，只能自己实现分派。

本模块全部是纯函数，不依赖 NoneBot 运行时，可直接被探针脚本 import。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

CAR_PATTERN = re.compile(r"^(\d{5,6})(.*)$", re.DOTALL)
r"""车牌：开头 5 或 6 位数字，其余全部作为备注。

`re.DOTALL` 是必需的，不是噪音：QQ 消息可以带换行，没有它 `.` 匹配不到换行符，
多行车牌会被拦腰截断。`\d{5,6}` 贪婪取位数，7 位以上数字开头时取前 6 位、
余下进备注——这与上游一致（koishi 用无边界的 `/^(\d{6})/`，nonebot-tsugu 用贪婪的
`^(\d{5,6})`），不要加 `(?!\d)` 之类去"纠正"。"""

MODE_SHORTCUT = re.compile(r"^(.+服)模式$")
STATUS_SHORTCUT = re.compile(r"^(.+服)玩家状态$")
"""两个 shortcut，与上游逐字一致（koishi `/^(.+服)模式$/`）。"""


@dataclass(frozen=True)
class Match:
    """一次成功的命令匹配。"""

    command: str
    """命令 ID，如 search_card。"""

    head: str
    """实际命中的命令头，用于生成帮助提示。"""

    args: list[str] = field(default_factory=list)
    """按空白切分后的参数。"""


def normalize(text: str) -> str:
    """剥掉首尾空白。

    event.get_message().extract_plain_text() 会去掉 @bot 但留下前导空格。
    """
    return text.strip()


def build_head_table(heads: Iterable[tuple[str, str]]) -> dict[str, str]:
    """把 (命令头, 命令ID) 按命令头长度降序排成查找表。

    保持插入顺序很关键：dict 在 3.7+ 保证插入顺序，遍历时「查卡面」
    一定先于「查卡」被尝试，前缀冲突由此消解。
    """
    ordered = sorted(heads, key=lambda pair: len(pair[0]), reverse=True)
    return dict(ordered)


def match_command(
    text: str,
    table: dict[str, str],
    *,
    no_space: bool = False,
) -> Match | None:
    """在 text 里匹配命令头。没有命中返回 None。

    no_space=False（默认）时命令头之后必须是空白或字符串结束；
    no_space=True 时额外允许「查卡947」这种无空格写法。
    """
    for head, command in table.items():
        if not text.startswith(head):
            continue
        rest = text[len(head) :]
        if rest and not no_space and not rest[0].isspace():
            continue
        return Match(command=command, head=head, args=rest.split())
    return None


def apply_shortcut(text: str) -> str:
    """把 mainline Tsugu 的两个 shortcut 正则改写成等价的标准命令。

    日服模式      -> 主服务器 日服
    国服玩家状态  -> 玩家状态 国服
    """
    if matched := MODE_SHORTCUT.match(text):
        return f"主服务器 {matched.group(1)}"
    if matched := STATUS_SHORTCUT.match(text):
        return f"玩家状态 {matched.group(1)}"
    return text


def match_car(
    text: str,
    car_keywords: Iterable[str],
    fake_keywords: Iterable[str],
) -> tuple[int, str] | None:
    """识别车牌消息。

    规则：以 5 或 6 位数字开头，其余部分包含至少一个车牌关键词，
    且不包含任何反关键词。命中返回 (房间号, 房间号之后的原文)。
    """
    matched = CAR_PATTERN.match(text)
    if matched is None:
        return None

    rest = matched.group(2)
    lowered = rest.lower()
    if not any(keyword in lowered for keyword in car_keywords):
        return None
    if any(keyword in lowered for keyword in fake_keywords):
        return None
    return int(matched.group(1)), rest


def get_group_openid(event: object) -> str | None:
    """取出群 openid；私聊事件没有这个字段。"""
    return getattr(event, "group_openid", None)
```

- [ ] **Step 2: 写探针脚本验证分派**

写到 `$CLAUDE_JOB_DIR/tmp/probe_rule.py`（一次性脚本，不入库）：

```python
import sys

sys.path.insert(0, "src/plugins")

import nonebot

# tsugu/__init__.py 在 import 时就会调用 get_plugin_config，必须先初始化 NoneBot
nonebot.init()

from tsugu import constants as const
from tsugu.rule import (
    apply_shortcut,
    build_head_table,
    match_car,
    match_command,
    normalize,
)

table = build_head_table(const.COMMAND_HEADS)

# 模拟「@bot 查卡 1399」经 extract_plain_text 后的样子
text = normalize(" 查卡 1399")
m = match_command(text, table)
assert m is not None and m.command == "search_card", m
assert m.args == ["1399"], m.args
assert m.head == "查卡", m.head

# 无空格开关的两种行为
assert match_command("查卡947", table, no_space=False) is None
m = match_command("查卡947", table, no_space=True)
assert m is not None and m.command == "search_card" and m.args == ["947"], m

# 前缀冲突：长命令头必须赢
assert match_command("查卡面 1399", table).command == "card_illustration"
assert match_command("查卡牌 1399", table).command == "search_card"
assert match_command("查卡池 922", table).command == "search_gacha"
assert match_command("抽卡模拟 300", table).command == "gacha_simulate"
assert match_command("抽卡 on", table).command == "gacha_switch"
assert match_command("玩家状态列表", table).command == "player_list"
assert match_command("玩家状态", table).command == "player_status"

# 多词参数原样保留
m = match_command("查卡 绿 tsugu", table)
assert m.args == ["绿", "tsugu"], m.args

# shortcut
assert apply_shortcut("日服模式") == "主服务器 日服"
assert apply_shortcut("国服玩家状态") == "玩家状态 国服"
assert apply_shortcut("查卡 1399") == "查卡 1399"
m = match_command(apply_shortcut("日服模式"), table)
assert m.command == "main_server" and m.args == ["日服"], m

# 车牌
assert match_car("123456 大分e", const.CAR_KEYWORDS, const.FAKE_KEYWORDS) == (123456, " 大分e")
assert match_car("12345 q1", const.CAR_KEYWORDS, const.FAKE_KEYWORDS) == (12345, " q1")
assert match_car("123456 雀魂", const.CAR_KEYWORDS, const.FAKE_KEYWORDS) is None   # fake 词
assert match_car("123456 随便聊聊", const.CAR_KEYWORDS, const.FAKE_KEYWORDS) is None  # 无 car 词
assert match_car("1234 大分e", const.CAR_KEYWORDS, const.FAKE_KEYWORDS) is None   # 位数不足
# 注意：这条 fixture 必须用真关键词 大分e。若写 "1234 大分车"，它是因为不含车牌关键词
# 而被拒的，而不是因为位数不足——那样就测不到位数规则。
assert match_car("1234567 大分e", const.CAR_KEYWORDS, const.FAKE_KEYWORDS) == (123456, "7 大分e")
# 上面这条是**故意的**：7 位数字开头时取前 6 位、余下留给备注，与上游一致
#（koishi 用 /^(\d{6})/ 无边界，nonebot-tsugu 用贪婪的 ^(\d{5,6})，两者都截断）。
# 不要"修"成拒绝 7 位——那会偏离上游行为。
assert match_car("查卡 1399", const.CAR_KEYWORDS, const.FAKE_KEYWORDS) is None     # 非数字开头

# 空参数与纯命令头
m = match_command("ycx", table)
assert m.command == "cutoff" and m.args == [], m

print("rule 探针全部通过")
```

- [ ] **Step 3: 运行探针，确认全绿**

```bash
cd /Users/tano/Documents/GitHub/personal/kasumi_bot
.venv/bin/python "$CLAUDE_JOB_DIR/tmp/probe_rule.py"
```

Expected: 打印 `rule 探针全部通过`，无 AssertionError。

如果某个断言失败，**先修 `rule.py` 而不是改断言**——这些断言直接来自规格，是对外行为契约。

- [ ] **Step 4: 静态检查并提交**

```bash
.venv/bin/ruff check src/ && .venv/bin/ruff format src/ && .venv/bin/pyright src/
git add -A
git commit -m "feat: 新增 QQ 触发层，支持命令头匹配、shortcut 与车牌识别"
```

---

### Task 4: 响应转换与发送

把 Tsugu 后端的 `[{type, string}]` 列表翻译成 QQ 消息，并处理单次回复最多 5 条被动消息的平台限制。

**Files:**
- Create: `src/plugins/tsugu/sender.py`

**Interfaces:**
- Consumes: 无（只依赖 nonebot-adapter-qq）
- Produces:
  - `sender.Response = _Response`（库声明的响应类型）
  - `sender.Part = str | bytes`（str = 一条文本消息，bytes = 一张图片）
  - `sender.split_messages(items: Response, limit: int) -> list[Part]`（纯函数）
  - `sender.build_message(part: Part) -> Message`
  - `sender.send_result(matcher, items, *, limit, at_user_id=None) -> None`（async）

- [ ] **Step 1: 写 sender.py**

```python
"""把 Tsugu 后端的响应列表翻译成 QQ 消息并发送。

后端所有查询接口统一返回 [{type: 'string'|'base64', string: ...}]。
QQ 官方平台限制同一个 msg_id 最多回复 5 条被动消息，所以不能一对一地发，
需要合并文本、并把超出部分截断。
"""

from __future__ import annotations

from base64 import b64decode
from typing import TYPE_CHECKING

from nonebot.adapters.qq import Message, MessageSegment
from tsugu_api_core._typing import _Response

if TYPE_CHECKING:
    from nonebot.matcher import Matcher

Response = _Response
"""Tsugu 后端的统一响应结构，直接用库声明的类型。"""

Part = str | bytes
"""一条待发送的消息：str 是文本，bytes 是图片二进制。"""


def split_messages(items: Response, limit: int) -> list[Part]:
    """把后端响应合并、截断成待发送的消息序列。

    连续的 string 段合并为一条文本消息；每个 base64 段单独作为一条图片消息。
    合并后的条数超过 limit 时，只保留前 limit - 1 条，末尾追加一条截断提示，
    这样总条数仍不超过 limit。
    """
    limit = max(limit, 1)

    parts: list[Part] = []
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            parts.append("".join(buffer))
            buffer.clear()

    for item in items:
        if item.get("type") == "base64":
            flush()
            parts.append(b64decode(item["string"]))
        else:
            buffer.append(item.get("string", ""))
    flush()

    if len(parts) <= limit:
        return parts
    return [*parts[: limit - 1], f"结果过长，仅显示前 {limit - 1} 项"]


def build_message(part: Part) -> Message:
    """把单个 Part 组装成 QQ 消息。

    图片用 file_image 产生 file_type=1 的 LocalAttachment，适配器据此识别为图片。

    这里不传 file_name，但它**不影响走哪条上传路径**：
    适配器的 `_extract_qq_media` 只在 `file_data` 超过 10MB 时才往 kwargs 里塞
    `file_name`，`send_to_group` 再按「kwargs 里有没有 file_name」在
    `post_group_upload`（分块）与 `post_group_files`（普通）之间二选一。
    所以约 310KB 的图片**传不传 file_name 都走普通上传**；反过来，任何 ≥10MB 的
    图片都会自动走分块上传，这一点本模块无法干预。
    """
    if isinstance(part, str):
        return Message(MessageSegment.text(part))
    return Message(MessageSegment.file_image(part))


async def send_result(
    matcher: type[Matcher],
    items: Response,
    *,
    limit: int,
    at_user_id: str | None = None,
) -> None:
    """按顺序发出全部消息。

    msg_id 与自增的 msg_seq 由 nonebot-adapter-qq 的 Bot.send 自动填充，
    这里不要自己维护，也不要跨事件复用同一个 matcher 的发送。
    """
    parts = split_messages(items, limit)
    if not parts:
        return

    for index, part in enumerate(parts):
        message = build_message(part)
        if index == 0 and at_user_id is not None:
            message = Message(MessageSegment.mention_user(at_user_id)) + " " + message
        await matcher.send(message)
```

- [ ] **Step 2: 写探针脚本验证拆分逻辑**

写到 `$CLAUDE_JOB_DIR/tmp/probe_sender.py`：

```python
import sys
from base64 import b64encode

sys.path.insert(0, "src/plugins")

import nonebot

# tsugu/__init__.py 在 import 时就会调用 get_plugin_config，必须先初始化 NoneBot
nonebot.init()

from nonebot.adapters.qq import Message

from tsugu.sender import build_message, split_messages

PNG = b"\x89PNG\r\n\x1a\n" + b"fake"
B64 = b64encode(PNG).decode()


def img():
    return {"type": "base64", "string": B64}


def txt(s):
    return {"type": "string", "string": s}


# 连续文本合并成一条
assert split_messages([txt("a"), txt("b")], 5) == ["ab"]

# 图片各自成条
assert split_messages([txt("a"), img()], 5) == ["a", PNG]
assert split_messages([img(), img()], 5) == [PNG, PNG]

# 未超上限时原样发出
assert len(split_messages([txt("a"), img(), img(), img()], 5)) == 4

# 超上限：保留前 limit-1 条 + 一条提示
parts = split_messages([img(), img(), img(), img(), img(), img()], 5)
assert len(parts) == 5, len(parts)
assert parts[:4] == [PNG] * 4
assert parts[4] == "结果过长，仅显示前 4 项", parts[4]

# limit=1 的退化情形
parts = split_messages([img(), img()], 1)
assert parts == ["结果过长，仅显示前 0 项"], parts

# limit 传 0 也不该崩
assert len(split_messages([img(), img()], 0)) == 1

# 空响应
assert split_messages([], 5) == []

# 错误响应就是一个普通文本
assert split_messages([txt("错误: 该卡不存在")], 5) == ["错误: 该卡不存在"]

# build_message 的形状
m = build_message("hello")
assert isinstance(m, Message) and m[0].type == "text"

m = build_message(PNG)
assert m[0].type == "file_image", m[0].type
assert m[0].data["content"] == PNG
# file_name 只是记录当前调用风格；它并不影响上传路径（见 build_message 的说明）
assert m[0].data["file_name"] is None

print("sender 探针全部通过")
```

- [ ] **Step 3: 运行探针，确认全绿**

```bash
cd /Users/tano/Documents/GitHub/personal/kasumi_bot
.venv/bin/python "$CLAUDE_JOB_DIR/tmp/probe_sender.py"
```

Expected: 打印 `sender 探针全部通过`。

- [ ] **Step 4: 静态检查并提交**

```bash
.venv/bin/ruff check src/ && .venv/bin/ruff format src/ && .venv/bin/pyright src/
git add -A
git commit -m "feat: 新增响应转换层，处理被动消息条数上限与图片发送"
```

---

### Task 5: 后端调用封装

把 `tsugu_api_async` 包一层，保证**所有**查询函数都返回 `Response`（失败时返回单个错误文本段），这样上层不用区分成功与失败两条路径。

**Files:**
- Create: `src/plugins/tsugu/api.py`

**Interfaces:**
- Consumes: `constants` 的表与文案
- Produces:
  - `api.Response = _Response`（库声明的响应类型）
  - `api.UserDataError(Exception)`：用户数据接口失败，`str(exc)` 可直接展示
  - `api.describe_error(exc) -> str`
  - `api.resolve_server(name) -> int`（async，失败抛 `ValueError`）
  - `api.resolve_difficulty(name) -> int`（async，失败抛 `ValueError`）
  - `api.load_user(user_id) -> _TsuguUser`（async）
  - `api.change_user(user_id, update: PartialTsuguUser) -> str | None`（async，成功返回 None）
  - `api.request_bind_code(user_id) -> int`（async）
  - `api.verify_bind(user_id, server, player_id, action) -> str`（async）
  - 一组同名查询函数，全部 `async` 且返回 `Response`：`search_card`、`card_illustration`、`search_character`、`search_event`、`search_gacha`、`search_song`、`song_chart`、`song_random`、`song_meta`、`event_stage`、`search_player`、`gacha_simulate`、`cutoff_detail`、`cutoff_all`、`cutoff_history`、`render_room_list`
  - **例外**：`api.query_all_rooms() -> list[_Room]` —— 车站接口不返回 Response 列表而返回房间字典列表，失败时抛 `UserDataError`

- [ ] **Step 1: 写 api.py**

```python
"""Tsugu 后端调用封装。

查询类接口在后端统一返回 [{type: 'string'|'base64', string: ...}]，业务错误
也是数组里的一个 string 段。这里把异常也收敛成同样的形状，于是调用方只需
处理一种返回类型。
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, cast

import nonebot
import tsugu_api_async
from tsugu_api_core._typing import (
    PartialTsuguUser,
    ServerId,
    _BindingAction,
    _DifficultyId,
    _Response,
    _Room,
    _TsuguUser,
)
from tsugu_api_core.exception import (
    BadRequestError,
    FailedException,
    HTTPStatusError,
    TsuguException,
)

from . import constants as const

if TYPE_CHECKING:
    from collections.abc import Awaitable, Sequence

Response = _Response
"""Tsugu 后端的统一响应结构，直接用库声明的类型。"""


class UserDataError(Exception):
    """用户数据接口返回失败。str(exc) 是可直接展示的中文文案。"""


def _error(text: str) -> Response:
    return [{"type": "string", "string": text}]


def _platform() -> str:
    """读取配置里的平台标识。"""
    from nonebot import get_plugin_config

    from .config import Config

    return get_plugin_config(Config).tsugu_platform


def describe_error(exc: BaseException) -> str:
    """把 tsugu_api 抛出的异常翻译成给用户看的中文文案。"""
    if isinstance(exc, BadRequestError):
        return const.HTTP_ERROR_TEXTS[400]
    if isinstance(exc, FailedException):
        if exc.status_code == HTTPStatus.UNPROCESSABLE_ENTITY:
            return f"错误: 无效的请求 ({exc.data})"
        return const.HTTP_ERROR_TEXTS.get(exc.status_code, str(exc.data))

    if isinstance(exc, HTTPStatusError):
        return const.ERR_NETWORK

    if isinstance(exc, TsuguException):
        # 基类 TsuguException 的 msg 本身就是给用户看的中文
        # （如车站的 RoomQueryFailure / RoomSubmitFailure）
        return str(exc)

    return const.ERR_NETWORK


async def _query(coro: Awaitable[Response]) -> Response:
    """执行一次后端查询，把任何异常收敛成错误文本响应。"""
    try:
        return await coro
    except Exception as exc:  # noqa: BLE001 - 网络/超时/解析错误都要收敛成文案
        nonebot.logger.opt(exception=exc).debug("Tsugu 后端查询失败")
        return _error(describe_error(exc))


# ---- 名称解析 ----


async def resolve_server(name: str) -> ServerId:
    """把服务器名解析成 ServerId。

    先查本地表（英文代号 / 中文全名 / 数字），未命中再走后端模糊搜索。
    失败抛 ValueError，文案已可直接展示。
    """
    # 表里所有键都是小写，所以只查小写形式即可覆盖精确输入
    if (server_id := const.SERVER_NAME_TO_ID.get(name.lower())) is not None:
        return server_id

    try:
        found = (await tsugu_api_async.fuzzy_search(name))["data"].get("server", [])
    except Exception as exc:
        nonebot.logger.opt(exception=exc).debug("服务器名模糊搜索失败")
        raise ValueError(const.ERR_SERVER_NOT_FOUND) from exc

    # 后端模糊搜索返回的是无类型的 str | int，这里收窄成 ServerId
    if not found or found[0] not in const.SERVER_ID_TO_NAME:
        raise ValueError(const.ERR_SERVER_NOT_FOUND)
    return cast("ServerId", found[0])


async def resolve_difficulty(name: str) -> _DifficultyId:
    """把难度名解析成 DifficultyId。失败抛 ValueError，文案已可直接展示。"""
    if (difficulty_id := const.DIFFICULTY_NAMES.get(name.lower())) is not None:
        return difficulty_id

    try:
        found = (await tsugu_api_async.fuzzy_search(name))["data"].get("difficulty", [])
    except Exception as exc:
        nonebot.logger.opt(exception=exc).debug("难度名模糊搜索失败")
        raise ValueError(const.ERR_DIFFICULTY_NOT_FOUND) from exc

    if not found or found[0] not in (0, 1, 2, 3, 4):
        raise ValueError(const.ERR_DIFFICULTY_NOT_FOUND)
    return cast("_DifficultyId", found[0])


# ---- 用户数据 ----


async def load_user(user_id: str) -> _TsuguUser:
    """读取用户数据。后端对不存在的用户会自动创建。"""
    try:
        response = await tsugu_api_async.get_user_data(_platform(), user_id)
    except Exception as exc:
        nonebot.logger.opt(exception=exc).debug("读取用户数据失败")
        raise UserDataError(describe_error(exc)) from exc

    if response.get("status") != "success":
        raise UserDataError(str(response.get("data", "错误: 获取用户数据失败")))
    return response["data"]


async def change_user(user_id: str, update: PartialTsuguUser) -> str | None:
    """写入用户数据。成功返回 None，失败返回可直接展示的错误文案。"""
    try:
        response = await tsugu_api_async.change_user_data(_platform(), user_id, update)
    except Exception as exc:  # noqa: BLE001 - 网络/超时/解析错误都要收敛成文案
        nonebot.logger.opt(exception=exc).debug("写入用户数据失败")
        return describe_error(exc)

    if response.get("status") != "success":
        return str(response.get("data", "错误: 修改用户数据失败"))
    return None


async def request_bind_code(user_id: str) -> int:
    """申请绑定验证码。"""
    try:
        response = await tsugu_api_async.bind_player_request(_platform(), user_id)
    except Exception as exc:
        nonebot.logger.opt(exception=exc).debug("申请绑定验证码失败")
        raise UserDataError(describe_error(exc)) from exc

    if response.get("status") != "success":
        raise UserDataError(str(response.get("data", "错误: 申请验证码失败")))
    return int(response["data"]["verifyCode"])


async def verify_bind(
    user_id: str, server: ServerId, player_id: int, action: _BindingAction
) -> str:
    """提交绑定或解绑验证。返回后端给的提示文本。"""
    try:
        response = await tsugu_api_async.bind_player_verification(
            _platform(), user_id, server, player_id, action
        )
    except Exception as exc:
        nonebot.logger.opt(exception=exc).debug("绑定验证失败")
        raise UserDataError(describe_error(exc)) from exc

    if response.get("status") != "success":
        raise UserDataError(str(response.get("data", "错误: 绑定验证失败")))
    return str(response["data"])


# ---- 查询接口 ----


async def search_card(servers: Sequence[ServerId], text: str) -> Response:
    return await _query(tsugu_api_async.search_card(servers, text=text))


async def card_illustration(card_id: int) -> Response:
    return await _query(tsugu_api_async.get_card_illustration(card_id))


async def search_character(servers: Sequence[ServerId], text: str) -> Response:
    return await _query(tsugu_api_async.search_character(servers, text=text))


async def search_event(servers: Sequence[ServerId], text: str) -> Response:
    return await _query(tsugu_api_async.search_event(servers, text=text))


async def search_gacha(servers: Sequence[ServerId], gacha_id: int) -> Response:
    return await _query(tsugu_api_async.search_gacha(servers, gacha_id))


async def search_song(servers: Sequence[ServerId], text: str) -> Response:
    return await _query(tsugu_api_async.search_song(servers, text=text))


async def song_chart(
    servers: Sequence[ServerId], song_id: int, difficulty_id: _DifficultyId
) -> Response:
    return await _query(tsugu_api_async.song_chart(servers, song_id, difficulty_id))


async def song_random(server: ServerId, text: str) -> Response:
    return await _query(tsugu_api_async.song_random(server, text=text))


async def song_meta(servers: Sequence[ServerId], server: ServerId) -> Response:
    return await _query(tsugu_api_async.song_meta(servers, server))


async def event_stage(
    server: ServerId, event_id: int | None, *, meta: bool
) -> Response:
    return await _query(tsugu_api_async.event_stage(server, event_id, meta))


async def search_player(player_id: int, server: ServerId) -> Response:
    return await _query(tsugu_api_async.search_player(player_id, server))


async def gacha_simulate(
    server: ServerId, times: int | None, gacha_id: int | None
) -> Response:
    return await _query(tsugu_api_async.gacha_simulate(server, times, gacha_id))


async def cutoff_detail(server: ServerId, tier: int, event_id: int | None) -> Response:
    return await _query(tsugu_api_async.cutoff_detail(server, tier, event_id))


async def cutoff_all(server: ServerId, event_id: int | None) -> Response:
    return await _query(tsugu_api_async.cutoff_all(server, event_id))


async def cutoff_history(server: ServerId, tier: int, event_id: int | None) -> Response:
    return await _query(
        tsugu_api_async.cutoff_list_of_recent_event(server, tier, event_id)
    )


async def query_all_rooms() -> list[_Room]:
    """车站里的全部房间号。

    注意这个接口不返回 Response 列表而是房间字典列表，为了和查询接口
    区分开，失败时抛 UserDataError 而不是返回错误文本段。
    """
    try:
        response = await tsugu_api_async.station_query_all_room()
    except Exception as exc:
        nonebot.logger.opt(exception=exc).debug("查询车站失败")
        raise UserDataError(describe_error(exc)) from exc

    if response.get("status") != "success":
        raise UserDataError(str(response.get("data", "错误: 查询车站失败")))
    return list(response["data"])


async def render_room_list(rooms: list[_Room]) -> Response:
    """把房间列表交给后端画成图片。"""
    return await _query(tsugu_api_async.room_list(rooms))
```

- [ ] **Step 2: 写探针脚本，对公共后端发真实请求**

写到 `$CLAUDE_JOB_DIR/tmp/probe_api.py`：

```python
import asyncio
import sys

sys.path.insert(0, "src/plugins")

import nonebot

# tsugu/__init__.py 在 import 时就会调用 get_plugin_config，必须先初始化 NoneBot
nonebot.init()

import tsugu_api_async

from tsugu import api

# 直接用库的默认后端地址，不经过 nonebot 配置
tsugu_api_async.settings.backend_url = "http://tsugubot.com:8080"
tsugu_api_async.settings.userdata_backend_url = "http://tsugubot.com:8080"
tsugu_api_async.settings.timeout = 60
tsugu_api_async.settings.compress = True
tsugu_api_async.settings.use_easy_bg = False


async def main():
    # 名称解析：本地表命中，不该发网络请求
    assert await api.resolve_server("cn") == 3
    assert await api.resolve_server("国服") == 3
    assert await api.resolve_server("JP") == 0
    assert await api.resolve_difficulty("expert") == 3
    assert await api.resolve_difficulty("简单") == 0

    # 本地表未命中时走后端模糊搜索
    assert await api.resolve_server("日本服") == 0
    assert await api.resolve_difficulty("ex") == 3

    try:
        await api.resolve_difficulty("这不是难度")
    except ValueError as exc:
        assert "难度" in str(exc), exc
    else:
        raise AssertionError("应当抛 ValueError")

    # 查询接口返回 base64 图片
    result = await api.search_song([3, 1], "1")
    assert isinstance(result, list) and result, result
    assert result[0]["type"] == "base64", result[0]["type"]
    assert len(result[0]["string"]) > 1000

    # 查卡面
    result = await api.card_illustration(1399)
    assert result[0]["type"] == "base64", result[0]

    # 错误路径：不存在的卡应当返回 string 段而不是抛异常
    result = await api.search_card([3], "999999999")
    assert isinstance(result, list) and result
    print("  查卡 999999999 ->", result[0]["type"], result[0]["string"][:50])

    # 车站
    rooms = await api.query_all_rooms()
    assert isinstance(rooms, list), rooms
    print("  车站房间数:", len(rooms))

    # 用户数据：用一个明显是测试用的 ID，后端会自动创建
    user = await api.load_user("probe-test-user")
    assert user["mainServer"] in (0, 1, 2, 3, 4), user
    assert isinstance(user["displayedServerList"], list), user
    assert isinstance(user["userPlayerList"], list), user
    print("  用户数据:", {k: user[k] for k in ("mainServer", "displayedServerList", "shareRoomNumber")})

    # 错误映射
    assert "参数错误" in api.describe_error(
        api.BadRequestError("/searchCard", {"status": "failed", "data": "参数错误", "error": []})
    )
    print("api 探针全部通过")


asyncio.run(main())
```

- [ ] **Step 3: 运行探针**

```bash
cd /Users/tano/Documents/GitHub/personal/kasumi_bot
.venv/bin/python "$CLAUDE_JOB_DIR/tmp/probe_api.py"
```

Expected: 打印若干行诊断信息，最后 `api 探针全部通过`。

若出现网络超时，检查 `tsugu_api_async.settings.timeout` 是否被设成了 60——公共后端渲染图片偶发超过默认的 10 秒。

- [ ] **Step 4: 静态检查并提交**

```bash
.venv/bin/ruff check src/ && .venv/bin/ruff format src/ && .venv/bin/pyright src/
git add -A
git commit -m "feat: 新增 Tsugu 后端调用封装与异常文案映射"
```

---

### Task 6: 用户数据与玩家选择

用户数据的读取、写入、玩家绑定选择规则，以及绑定流程要用的文本构造。

**Files:**
- Create: `src/plugins/tsugu/user.py`

**Interfaces:**
- Consumes: `api.load_user`、`api.change_user`、`api.request_bind_code`、`api.verify_bind`、`api.UserDataError`、`constants`
- Produces:
  - `user.User` dataclass：字段 `main_server`、`displayed_server_list`、`share_room_number`、`user_player_index`、`user_player_list`
  - `user.User.from_raw(raw) -> User`
  - `user.load_user_or_finish(matcher, user_id) -> User`（async，失败时已 `finish`）
  - `user.pick_player(user, server=None, index=None) -> _UserPlayerInList`（失败抛 `ValueError`）
  - `user.build_player_list_text(user) -> str`（纯函数）
  - `user.build_bind_prompt(server, code) -> str`（纯函数）
  - `user.pending: dict[str, PendingBind]`：绑定流程的待处理状态

- [ ] **Step 1: 写 user.py**

```python
"""用户数据模型、玩家绑定选择规则与绑定流程状态。

平台标识固定为配置里的 TSUGU_PLATFORM（默认 "red"），与官方 Tsugu QQ Bot
共用同一份用户数据命名空间。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from . import api
from . import constants as const

if TYPE_CHECKING:
    from nonebot.matcher import Matcher
    from tsugu_api_core._typing import (
        ServerId,
        _BindingAction,
        _TsuguUser,
        _UserPlayerInList,
    )


@dataclass
class User:
    """用户数据的可读视图。字段名与后端 tsuguUser 一一对应。"""

    main_server: ServerId = 3
    displayed_server_list: list[ServerId] = field(default_factory=lambda: [3, 0])
    share_room_number: bool = True
    user_player_index: int = 0
    user_player_list: list[_UserPlayerInList] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: _TsuguUser) -> "User":
        # 下标取值而非 .get(默认值)：_TsuguUser 把字段都声明为必填，给不存在的
        # 字段编默认值只会掩盖后端契约被破坏这件事。
        return cls(
            main_server=raw["mainServer"],
            displayed_server_list=list(raw["displayedServerList"]),
            share_room_number=raw["shareRoomNumber"],
            user_player_index=raw["userPlayerIndex"],
            user_player_list=list(raw["userPlayerList"]),
        )


@dataclass
class PendingBind:
    """等待用户回复玩家 ID 的绑定流程。"""

    action: _BindingAction
    """'bind' 或 'unbind'。"""

    server: ServerId
    created_at: float = field(default_factory=time.monotonic)
    """创建时刻，用于超时判断。"""

    player_id: int | None = None
    """解绑时已确定要解绑的玩家；绑定时为 None。"""


pending: dict[str, PendingBind] = {}
"""用户 ID -> 待处理的绑定流程。进程内存，重启即失效，这是期望行为。"""


def server_name(server: ServerId) -> str:
    """服务器 ID 转中文名。"""
    return const.SERVER_ID_TO_NAME.get(server, str(server))


async def load_user_or_finish(matcher: type[Matcher], user_id: str) -> User:
    """读取用户数据；失败时直接结束本次回复。

    matcher.finish 会抛 FinishedException，所以成功路径以外不会返回。
    """
    try:
        raw = await api.load_user(user_id)
    except api.UserDataError as exc:
        await matcher.finish(str(exc))
        raise
    return User.from_raw(raw)


def pick_player(
    user: User, server: ServerId | None = None, index: int | None = None
) -> _UserPlayerInList:
    """按 mainline Tsugu 的规则选出要展示的玩家绑定。

    index 给定时按 1 起的序号取；否则先看默认索引那条是不是在目标服务器上，
    不是的话取列表中第一条属于目标服务器的绑定。失败抛 ValueError。
    """
    players = user.user_player_list
    if not players:
        raise ValueError(const.ERR_NOT_BOUND_ANY)

    if index is not None:
        if index < 1 or index > len(players):
            raise ValueError(const.ERR_INDEX_INVALID)
        return players[index - 1]

    target = user.main_server if server is None else server
    if 0 <= user.user_player_index < len(players):
        default_player = players[user.user_player_index]
        if default_player["server"] == target:
            return default_player

    for player in players:
        if player["server"] == target:
            return player

    raise ValueError(const.ERR_NOT_BOUND_ON_SERVER)


def build_player_list_text(user: User) -> str:
    """玩家状态列表命令的纯文本回复。"""
    lines: list[str] = []
    if not user.user_player_list:
        lines.append(const.ERR_NOT_BOUND_ANY)
    else:
        lines.append("已绑定玩家列表:")
        for index, player in enumerate(user.user_player_list, 1):
            lines.append(
                f"{index}. {server_name(player['server'])}: {player['playerId']}"
            )
        lines.append(f"当前默认玩家绑定信息ID: {user.user_player_index + 1}")

    lines.append(f"当前主服务器: {server_name(user.main_server)}")
    lines.append(
        "默认显示服务器顺序: "
        + ", ".join(server_name(server) for server in user.displayed_server_list)
    )
    return "\n".join(lines)


def build_bind_prompt(server: ServerId, code: int) -> str:
    """绑定流程第一步的引导文本，措辞与 mainline Tsugu 一致。"""
    return (
        f"正在绑定来自 {server_name(server)} 账号，请将你的\n"
        "评论(个性签名)\n"
        "或者\n"
        "你的当前使用的卡组的卡组名(乐队编队名称)\n"
        "改为以下数字后，直接发送你的玩家id\n"
        f"{code}"
    )
```

- [ ] **Step 2: 写探针脚本**

写到 `$CLAUDE_JOB_DIR/tmp/probe_user.py`：

```python
import sys

sys.path.insert(0, "src/plugins")

import nonebot

# tsugu/__init__.py 在 import 时就会调用 get_plugin_config，必须先初始化 NoneBot
nonebot.init()

from tsugu import constants as const
from tsugu.user import User, build_bind_prompt, build_player_list_text, pick_player

# 未绑定任何玩家
user = User(user_player_list=[])
for kwargs in ({}, {"server": 0}, {"index": 1}):
    try:
        pick_player(user, **kwargs)
    except ValueError as exc:
        assert str(exc) == const.ERR_NOT_BOUND_ANY, exc
    else:
        raise AssertionError("应当抛 ValueError")

# 正常情况：默认索引那条就在主服务器上
user = User(
    main_server=3,
    user_player_index=0,
    user_player_list=[{"playerId": 10000000, "server": 3}, {"playerId": 40474621, "server": 0}],
)
assert pick_player(user, server=3)["playerId"] == 10000000
assert pick_player(user, server=0)["playerId"] == 40474621
assert pick_player(user)["playerId"] == 10000000          # 缺省用 main_server
assert pick_player(user, index=2)["playerId"] == 40474621

# 默认索引那条不在目标服务器上时，回退到列表中第一条该服务器的绑定
user = User(
    main_server=3,
    user_player_index=1,
    user_player_list=[
        {"playerId": 111, "server": 3},
        {"playerId": 222, "server": 0},
        {"playerId": 333, "server": 0},
    ],
)
assert pick_player(user, server=3)["playerId"] == 111

# 目标服务器上没有任何绑定
try:
    pick_player(user, server=2)
except ValueError as exc:
    assert str(exc) == const.ERR_NOT_BOUND_ON_SERVER, exc
else:
    raise AssertionError("应当抛 ValueError")

# 序号越界
for bad in (0, -1, 4):
    try:
        pick_player(user, index=bad)
    except ValueError as exc:
        assert str(exc) == const.ERR_INDEX_INVALID, exc
    else:
        raise AssertionError(f"index={bad} 应当抛 ValueError")

# 默认索引越界时不应崩溃，而是回退到遍历
user = User(
    main_server=3,
    user_player_index=99,
    user_player_list=[{"playerId": 111, "server": 3}],
)
assert pick_player(user, server=3)["playerId"] == 111

# 文本构造
user = User(
    main_server=3,
    displayed_server_list=[3, 0],
    user_player_index=0,
    user_player_list=[{"playerId": 10000000, "server": 3}, {"playerId": 40474621, "server": 0}],
)
text = build_player_list_text(user)
expected = (
    "已绑定玩家列表:\n"
    "1. 国服: 10000000\n"
    "2. 日服: 40474621\n"
    "当前默认玩家绑定信息ID: 1\n"
    "当前主服务器: 国服\n"
    "默认显示服务器顺序: 国服, 日服"
)
assert text == expected, repr(text)

# 未绑定时前三行塌缩成一行
text = build_player_list_text(User(user_player_list=[]))
assert text.startswith("未绑定任何玩家\n当前主服务器: 国服"), repr(text)

prompt = build_bind_prompt(0, 12345)
assert prompt.endswith("\n12345"), repr(prompt)
assert "正在绑定来自 日服 账号" in prompt, repr(prompt)

print("user 探针全部通过")
```

- [ ] **Step 3: 运行探针**

```bash
cd /Users/tano/Documents/GitHub/personal/kasumi_bot
.venv/bin/python "$CLAUDE_JOB_DIR/tmp/probe_user.py"
```

Expected: 打印 `user 探针全部通过`。

- [ ] **Step 4: 静态检查并提交**

```bash
.venv/bin/ruff check src/ && .venv/bin/ruff format src/ && .venv/bin/pyright src/
git add -A
git commit -m "feat: 新增用户数据模型、玩家选择规则与绑定文案"
```

---

### Task 7: 分派器、群级设置与卡池命令

把所有零件接起来：本地库、车牌监听、唯一的消息分派器，以及第一批端到端可跑的的命令。

**Files:**
- Create: `src/plugins/tsugu/db.py`
- Create: `src/plugins/tsugu/car.py`
- Create: `src/plugins/tsugu/commands/__init__.py`
- Create: `src/plugins/tsugu/commands/gacha.py`
- Modify: `src/plugins/tsugu/__init__.py`（把骨架换成完整分派器）
- Modify: `src/plugins/tsugu/api.py`（追加 `submit_room_number`）

**Interfaces:**
- Consumes: `rule`、`sender`、`api`、`user`、`constants`
- Produces:
  - `db.GroupSetting`、`db.is_gacha_enabled(group_openid)`、`db.set_gacha_enabled(group_openid, enabled)`
  - `car.maybe_forward(event, user_id, text) -> bool`（async）
  - `api.submit_room_number(number, raw_message, user_id, user_name, token) -> str`（async，空串表示成功）
  - `commands.Ctx`：dataclass，字段 `matcher`、`bot`、`event`、`user_id`、`group_openid`、`args`、`head`、`at_user_id`、`max_messages`、`pending`；方法 `reply(items)` / `reply_text(text)` / `reply_error(text)` / `local_only()`
  - `commands.HANDLERS: dict[str, Handler]`

- [ ] **Step 1: 写 db.py**

```python
"""群级设置的本地存储。

Tsugu 的用户数据 API 以用户为键，表达不了「本群」这个维度，所以群级设置
只能落本地。整个项目仅此一张表。
"""

from __future__ import annotations

from nonebot_plugin_orm import Model, get_session
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column


class GroupSetting(Model):
    """群级设置。"""

    __tablename__ = "tsugu_group_settings"

    group_openid: Mapped[str] = mapped_column(String(64), primary_key=True)
    gacha_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


async def is_gacha_enabled(group_openid: str) -> bool:
    """查不到该群的行时视为默认开启，只读操作不写库。"""
    session = get_session()
    async with session.begin():
        setting = await session.get(GroupSetting, group_openid)
        return True if setting is None else bool(setting.gacha_enabled)


async def set_gacha_enabled(group_openid: str, *, enabled: bool) -> None:
    """写入群级抽卡开关，不存在则插入。"""
    session = get_session()
    async with session.begin():
        setting = await session.get(GroupSetting, group_openid)
        if setting is None:
            session.add(GroupSetting(group_openid=group_openid, gacha_enabled=enabled))
        else:
            setting.gacha_enabled = enabled
```

- [ ] **Step 2: 给 api.py 追加 submit_room_number**

在 `api.py` 的「查询接口」段末尾追加：

```python
async def submit_room_number(
    number: int,
    raw_message: str,
    user_id: str,
    user_name: str,
    bandori_station_token: str | None,
) -> str:
    """提交车牌到车站。返回空串表示成功，否则是可直接展示的错误文案。"""
    try:
        response = await tsugu_api_async.station_submit_room_number(
            number,
            raw_message,
            _platform(),
            user_id,
            user_name,
            bandori_station_token=bandori_station_token,
        )
    except Exception as exc:  # noqa: BLE001 - 网络/超时/解析错误都要收敛成文案
        nonebot.logger.opt(exception=exc).debug("提交车牌失败")
        return describe_error(exc)

    if response.get("status") != "success":
        return str(response.get("data", "错误: 提交车牌失败"))
    return ""
```

- [ ] **Step 3: 写 car.py**

```python
"""车牌自动转发。

群聊里 Bot 只能收到 @ 了它的消息，所以「5/6 位数字开头」的车牌在群里根本
收不到；私聊里能正常工作。逻辑保持完整，将来拿到全量消息权限即自动生效。
"""

from __future__ import annotations

from typing import Any

import nonebot

from . import api
from . import constants as const
from .rule import match_car


async def maybe_forward(event: Any, user_id: str, text: str) -> bool:
    """识别并提交车牌。命中并提交成功返回 True，应当终止后续命令分派。"""
    car = match_car(text, const.CAR_KEYWORDS, const.FAKE_KEYWORDS)
    if car is None:
        return False

    number, _rest = car
    try:
        raw_user = await api.load_user(user_id)
    except api.UserDataError as exc:
        nonebot.logger.debug(f"车牌识别：读取用户数据失败 {exc}")
        return False

    if not raw_user.get("shareRoomNumber"):
        nonebot.logger.debug("车牌识别：该用户未开启车牌转发")
        return False

    from nonebot import get_plugin_config

    from .config import Config

    config = get_plugin_config(Config)
    # 昵称挂在 event.author.username 上（GroupMemberAuthor 与 FriendAuthor 都有），
    # 事件本身没有顶层 username 字段
    user_name = getattr(getattr(event, "author", None), "username", None) or user_id
    error = await api.submit_room_number(
        number,
        text,
        user_id,
        str(user_name),
        config.tsugu_bandori_station_token,
    )
    if error:
        nonebot.logger.warning(f"车牌识别：提交失败 {error}")
        return False

    nonebot.logger.debug(f"车牌识别：已提交房间 {number}")
    return True
```

- [ ] **Step 4: 写 commands/__init__.py**

```python
"""命令分派表与执行上下文。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import nonebot

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
        if command in HANDLERS:
            nonebot.logger.warning(f"命令 {command} 被重复注册，后者会覆盖前者")
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
```

- [ ] **Step 5: 写 commands/gacha.py**

```python
"""查卡池、抽卡模拟与群级抽卡开关。"""

from __future__ import annotations

from .. import api, db, user
from .. import constants as const
from . import Ctx, register


@register("search_gacha")
async def handle_search_gacha(ctx: Ctx) -> None:
    if not ctx.args:
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    if not ctx.args[0].lstrip("-").isdigit():
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(
        await api.search_gacha(tsugu_user.displayed_server_list, int(ctx.args[0]))
    )


@register("gacha_simulate")
async def handle_gacha_simulate(ctx: Ctx) -> None:
    if not ctx.args or not ctx.args[0].isdigit():
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    if ctx.group_openid is not None and not await db.is_gacha_enabled(ctx.group_openid):
        await ctx.reply_text(const.ERR_GACHA_DISABLED)
        return

    times = int(ctx.args[0])
    gacha_id = int(ctx.args[1]) if len(ctx.args) > 1 and ctx.args[1].isdigit() else None

    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(await api.gacha_simulate(tsugu_user.main_server, times, gacha_id))


async def _switch_gacha(ctx: Ctx, *, enabled: bool) -> None:
    if ctx.group_openid is None:
        await ctx.reply_text(const.ERR_GROUP_ONLY)
        return
    await db.set_gacha_enabled(ctx.group_openid, enabled=enabled)
    await ctx.reply_text("开启成功" if enabled else "关闭成功")


@register("gacha_switch")
async def handle_gacha_switch(ctx: Ctx) -> None:
    if not ctx.args:
        await ctx.reply_text("无效指令")
        return
    word = ctx.args[0]
    if word in ("on", "开启"):
        await _switch_gacha(ctx, enabled=True)
    elif word in ("off", "关闭"):
        await _switch_gacha(ctx, enabled=False)
    else:
        await ctx.reply_text("无效指令")


@register("gacha_on")
async def handle_gacha_on(ctx: Ctx) -> None:
    await _switch_gacha(ctx, enabled=True)


@register("gacha_off")
async def handle_gacha_off(ctx: Ctx) -> None:
    await _switch_gacha(ctx, enabled=False)
```

注意 `抽卡模拟` 对群级开关的判断放在参数校验**之后**：mainline 也是先校验 `times` 再查开关。而私聊（`group_openid is None`）永远放行。

- [ ] **Step 6: 把 __init__.py 换成完整分派器**

```python
"""Tsugu BanGDream Bot 的 QQ 官方 Bot 前端。

QQ 群里 Bot 只能收到 @ 了它的消息，@ 会被解析成 MentionUser 段，导致
nonebot 的 TrieRule 完全不匹配。所以这里只注册一个 on_message，自己做分派。
"""

from __future__ import annotations

import time

import nonebot
import tsugu_api_async
from nonebot import get_plugin_config, on_message

# 这两个必须是运行时导入：NoneBot 靠运行时求值注解来做依赖注入，
# 注解写成 Any 会直接抛 `ValueError: Unknown parameter bot`。
# ruff 的 TC002 认不出 @tsugu.handle() 是运行时求值装饰器，故显式豁免。
from nonebot.adapters.qq import Bot  # noqa: TC002
from nonebot.adapters.qq.event import QQMessageEvent  # noqa: TC002
from nonebot.plugin import PluginMetadata, require

# 必须早于下面任何相对导入：`from .commands import ...` 会连锁 import 到 db，
# 而 db 依赖 orm 的 Model / get_session。缺这一步会抛
# RuntimeError: Cannot detect caller plugin（orm 在导入期调 localstore 找调用方插件）。
require("nonebot_plugin_orm")

from . import car, user
from . import constants as const
from .commands import HANDLERS, Ctx
from .config import Config
from .rule import (
    apply_shortcut,
    build_head_table,
    get_group_openid,
    match_command,
    normalize,
)

__plugin_meta__ = PluginMetadata(
    name="tsugu",
    description="Tsugu BanGDream Bot 的 QQ 官方 Bot 前端",
    usage="发送「help」查看全部指令",
    config=Config,
    supported_adapters={"~qq"},
)

config: Config = get_plugin_config(Config)

tsugu_api_async.settings.backend_url = config.tsugu_backend_url
tsugu_api_async.settings.userdata_backend_url = config.tsugu_data_backend_url
tsugu_api_async.settings.timeout = config.tsugu_timeout
tsugu_api_async.settings.max_retries = config.tsugu_retries
tsugu_api_async.settings.proxy = config.tsugu_proxy
tsugu_api_async.settings.backend_proxy = config.tsugu_backend_proxy
tsugu_api_async.settings.userdata_backend_proxy = config.tsugu_data_backend_proxy
tsugu_api_async.settings.use_easy_bg = config.tsugu_use_easy_bg
tsugu_api_async.settings.compress = config.tsugu_compress


def _collect_heads() -> list[tuple[str, str]]:
    """静态命令头 + 用户在 .env 里追加的别名。

    别名字段是 Set[str]，在 .env 里必须写成 JSON 数组
    （`TSUGU_SEARCH_CARD_ALIASES=["查卡","查卡牌"]`）——NoneBot 对复杂类型的
    环境变量一律走 json.loads，写成逗号分隔会直接抛 SettingsError。
    """
    heads = list(const.COMMAND_HEADS)
    taken: dict[str, str] = dict(const.COMMAND_HEADS)

    aliases: list[tuple[str, str]] = []
    for field, command in const.ALIAS_FIELDS.items():
        for alias in getattr(config, field):
            owner = taken.get(alias)
            # 只在**指向不同命令**时才告警：给同一命令补一个它已有的别名
            # （例如给查曲加 "查曲"）是无操作，不该刷警告。
            if owner is not None and owner != command:
                nonebot.logger.warning(
                    f"配置的别名 {alias!r} 与已有命令头重名，"
                    f"将把 {owner!r} 改指向 {command!r}"
                )
            taken[alias] = command
            aliases.append((alias, command))

    heads.extend(aliases)
    return heads


HEAD_TABLE = build_head_table(_collect_heads())

tsugu = on_message(priority=10, block=True)


@tsugu.handle()
async def _dispatch(bot: Bot, event: QQMessageEvent) -> None:
    # 这两个注解必须是运行时导入的：NoneBot 靠运行时求值注解来做依赖注入，
    # 写成 Any 会直接抛 ValueError: Unknown parameter bot。
    user_id = event.get_user_id()
    text = normalize(event.get_message().extract_plain_text())
    if not text:
        return

    # 这里用 get 而不是 pop：绑定流程要能容忍用户输错一次再重试，
    # 由 bind_reply 处理器在**成功**时清掉。用 pop 的话任何一次输错都会
    # 终止流程（用户得重新申请验证码），tsugu_bind_timeout 也就失去意义了。
    pending = user.pending.get(user_id)
    if pending is not None:
        if time.monotonic() - pending.created_at > config.tsugu_bind_timeout:
            user.pending.pop(user_id, None)
            await tsugu.finish(const.ERR_BIND_TIMEOUT)
            return
        command, head, args = "bind_reply", "绑定玩家", [text]
    else:
        # 车牌自动转发优先于任何命令
        if await car.maybe_forward(event, user_id, text):
            return

        matched = match_command(
            apply_shortcut(text), HEAD_TABLE, no_space=config.tsugu_no_space
        )
        if matched is None:
            return
        command, head, args = matched.command, matched.head, matched.args

    handler = HANDLERS.get(command)
    if handler is None:
        nonebot.logger.warning(f"命令 {command} 没有注册处理器")
        return

    ctx = Ctx(
        matcher=tsugu,
        bot=bot,
        event=event,
        user_id=user_id,
        group_openid=get_group_openid(event),
        args=args,
        head=head,
        at_user_id=user_id if config.tsugu_at else None,
        max_messages=config.tsugu_max_messages,
        pending=pending,
    )
    await handler(ctx)
```

- [ ] **Step 7: 验证假事件能正确剥离 @ 并命中命令**

写到 `$CLAUDE_JOB_DIR/tmp/probe_event.py`：

```python
import sys

sys.path.insert(0, "src/plugins")

import nonebot

# tsugu/__init__.py 在 import 时就会调用 get_plugin_config，必须先初始化 NoneBot
nonebot.init()

from nonebot.adapters.qq.event import C2CMessageCreateEvent, GroupAtMessageCreateEvent

from tsugu import constants as const
from tsugu.rule import build_head_table, get_group_openid, match_command, normalize

table = build_head_table(const.COMMAND_HEADS)

# GroupAtMessageCreateEvent 的必填字段是 id / content / timestamp / group_id /
# group_openid / author，其中 author（GroupMemberAuthor）还要 id / bot / member_openid。
raw = {
    "id": "GROUP_AT_MESSAGE_CREATE:test",
    "author": {"id": "USER_OPENID", "bot": False, "member_openid": "MEMBER_OPENID"},
    "content": "<@!BOT_OPENID> 查卡 1399",
    "group_openid": "GROUP_OPENID",
    "group_id": "GROUP_ID",
    "timestamp": "2026-09-15T12:00:00+08:00",
}

event = GroupAtMessageCreateEvent.model_validate(raw)

# @bot 被剥掉，留下的前导空格由 normalize 去掉
plain = event.get_message().extract_plain_text()
assert "@" not in plain, repr(plain)
text = normalize(plain)
assert text == "查卡 1399", repr(text)

# 之后就是 Task 3 已经验证过的分派
m = match_command(text, table)
assert m is not None and m.command == "search_card" and m.args == ["1399"], m

# 群聊能取到 group_openid
assert get_group_openid(event) == "GROUP_OPENID", get_group_openid(event)

# 私聊事件取不到 group_openid（群级抽卡开关要靠这个判据区分场景）
c2c = C2CMessageCreateEvent.model_validate(
    {
        "id": "C2C_MESSAGE_CREATE:test",
        "author": {"id": "USER_OPENID", "user_openid": "USER_OPENID"},
        "content": "查卡 1399",
        "timestamp": "2026-09-15T12:00:00+08:00",
    }
)
assert get_group_openid(c2c) is None, get_group_openid(c2c)

# 昵称挂在 author.username 上，不在事件顶层——车牌转发取用户名靠它
assert getattr(event.author, "username", None) is None  # 本样本没给 username
assert getattr(c2c.author, "username", None) is None

print("event 探针全部通过：", repr(plain), "->", repr(text), "->", m.command, m.args)
```

- [ ] **Step 8: 运行假事件探针**

```bash
cd /Users/tano/Documents/GitHub/personal/kasumi_bot
.venv/bin/python "$CLAUDE_JOB_DIR/tmp/probe_event.py"
```

Expected: 打印 `event 探针全部通过： '<@!BOT_OPENID> 查卡 1399' ...` 之类的诊断行。

若 `model_validate` / `parse_obj` 都不可用，改用 `GroupAtMessageCreateEvent(**raw)` 并相应调整字段名——以适配器的实际事件模型为准。

- [ ] **Step 9: 验证本地库自动建表**

```bash
cd /Users/tano/Documents/GitHub/personal/kasumi_bot
rm -rf data
.venv/bin/python "$CLAUDE_JOB_DIR/tmp/boot_probe.py" 20 "$CLAUDE_JOB_DIR/tmp/boot.log"
grep -iE "orm|migrat|tsugu|error" "$CLAUDE_JOB_DIR/tmp/boot.log" | head -20
.venv/bin/python -c "
import sqlite3
tables = [r[0] for r in sqlite3.connect('data/db.sqlite3').execute(
    \"select name from sqlite_master where type='table'\")]
print('表:', sorted(tables))
assert 'tsugu_group_settings' in tables, tables
assert 'live_events' not in tables, '旧表没清掉'
cols = [r[1] for r in sqlite3.connect('data/db.sqlite3').execute(
    'pragma table_info(tsugu_group_settings)')]
assert 'group_openid' in cols and 'gacha_enabled' in cols, cols
print('本地库 OK')
"
```

Expected: 打印 `表: ['alembic_version', 'tsugu_group_settings']` 与 `本地库 OK`。

- [ ] **Step 10: 静态检查并提交**

```bash
.venv/bin/ruff check src/ && .venv/bin/ruff format src/ && .venv/bin/pyright src/
git add -A
git commit -m "feat: 接入消息分派器、车牌监听与群级抽卡开关"
```

---

### Task 8: 查询命令 — 卡与曲

第一批纯查询命令。参数校验失败时统一回复 `incomplete_cmd_text(head)`，即 mainline Tsugu 的 `错误: 指令不完整 / 使用以下指令以查看帮助: / help <命令名>`。

**Files:**
- Create: `src/plugins/tsugu/commands/card.py`
- Create: `src/plugins/tsugu/commands/character.py`
- Create: `src/plugins/tsugu/commands/song.py`

**Interfaces:**
- Consumes: `commands.Ctx`、`commands.register`、`api`、`user`、`constants`
- Produces: 向 `HANDLERS` 注册 `search_card`、`card_illustration`、`search_character`、`search_song`、`song_chart`、`song_random`、`song_meta`

- [ ] **Step 1: 写 commands/card.py**

```python
"""查卡与查卡面。"""

from __future__ import annotations

from .. import api, user
from .. import constants as const
from . import Ctx, register


@register("search_card")
async def handle_search_card(ctx: Ctx) -> None:
    if not ctx.args:
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(
        await api.search_card(tsugu_user.displayed_server_list, " ".join(ctx.args))
    )


@register("card_illustration")
async def handle_card_illustration(ctx: Ctx) -> None:
    if not ctx.args or not ctx.args[0].isdigit():
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    await ctx.reply(await api.card_illustration(int(ctx.args[0])))
```

- [ ] **Step 2: 写 commands/character.py**

```python
"""查角色。"""

from __future__ import annotations

from .. import api, user
from .. import constants as const
from . import Ctx, register


@register("search_character")
async def handle_search_character(ctx: Ctx) -> None:
    if not ctx.args:
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(
        await api.search_character(tsugu_user.displayed_server_list, " ".join(ctx.args))
    )
```

- [ ] **Step 3: 写 commands/song.py**

```python
"""查曲、查谱面、随机曲、查询分数表。"""

from __future__ import annotations

from .. import api, user
from .. import constants as const
from . import Ctx, register


@register("search_song")
async def handle_search_song(ctx: Ctx) -> None:
    if not ctx.args:
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(
        await api.search_song(tsugu_user.displayed_server_list, " ".join(ctx.args))
    )


@register("song_chart")
async def handle_song_chart(ctx: Ctx) -> None:
    if not ctx.args or not ctx.args[0].isdigit():
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    song_id = int(ctx.args[0])
    difficulty_id = const.DEFAULT_DIFFICULTY_ID
    if len(ctx.args) > 1:
        try:
            difficulty_id = await api.resolve_difficulty(ctx.args[1])
        except ValueError as exc:
            await ctx.reply_error(str(exc))
            return

    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(
        await api.song_chart(tsugu_user.displayed_server_list, song_id, difficulty_id)
    )


@register("song_random")
async def handle_song_random(ctx: Ctx) -> None:
    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(await api.song_random(tsugu_user.main_server, " ".join(ctx.args)))


@register("song_meta")
async def handle_song_meta(ctx: Ctx) -> None:
    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)

    server = tsugu_user.main_server
    if ctx.args:
        try:
            server = await api.resolve_server(ctx.args[0])
        except ValueError as exc:
            await ctx.reply_error(str(exc))
            return

    await ctx.reply(await api.song_meta(tsugu_user.displayed_server_list, server))
```

注意 `随机曲` 用 `main_server` 而不是 `displayed_server_list`（后端 `/songRandom` 只接受单个 `mainServer`），`查询分数表` 两个都传（`displayedServerList` 决定展示哪些服，`mainServer` 决定以哪个服为准）。

- [ ] **Step 4: 验证这批命令已注册**

```bash
cd /Users/tano/Documents/GitHub/personal/kasumi_bot
.venv/bin/python "$CLAUDE_JOB_DIR/tmp/boot_probe.py" 20 "$CLAUDE_JOB_DIR/tmp/boot.log"
tail -30 "$CLAUDE_JOB_DIR/tmp/boot.log"
grep -c "@register" src/plugins/tsugu/commands/*.py
```

Expected: `nb run` 无报错；`gacha.py` 5 处、`card.py` 2 处、`character.py` 1 处、`song.py` 4 处。

- [ ] **Step 5: 静态检查并提交**

```bash
.venv/bin/ruff check src/ && .venv/bin/ruff format src/ && .venv/bin/pyright src/
git add -A
git commit -m "feat: 新增查卡、查角色与查曲系列命令"
```

---

### Task 9: 查询命令 — 活动、档线、玩家与车站

**Files:**
- Create: `src/plugins/tsugu/commands/event.py`
- Create: `src/plugins/tsugu/commands/cutoff.py`
- Create: `src/plugins/tsugu/commands/player.py`
- Create: `src/plugins/tsugu/commands/station.py`

**Interfaces:**
- Consumes: `commands.Ctx`、`commands.register`、`api`、`user`、`constants`
- Produces: 向 `HANDLERS` 注册 `search_event`、`event_stage`、`cutoff`、`cutoff_all`、`cutoff_history`、`search_player`、`ycm`

- [ ] **Step 1: 写 commands/event.py**

```python
"""查活动与查试炼。"""

from __future__ import annotations

from .. import api, user
from .. import constants as const
from . import Ctx, register

META_FLAG = "-m"


@register("search_event")
async def handle_search_event(ctx: Ctx) -> None:
    if not ctx.args:
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(
        await api.search_event(tsugu_user.displayed_server_list, " ".join(ctx.args))
    )


@register("event_stage")
async def handle_event_stage(ctx: Ctx) -> None:
    # -m 可以从任意位置出现，先摘掉再按位置解析
    meta = META_FLAG in ctx.args
    positional = [arg for arg in ctx.args if arg != META_FLAG]

    event_id: int | None = None
    if positional:
        if not positional[0].isdigit():
            await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
            return
        event_id = int(positional[0])

    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(await api.event_stage(tsugu_user.main_server, event_id, meta=meta))
```

- [ ] **Step 2: 写 commands/cutoff.py**

```python
"""预测线：ycx / ycxall / lsycx。

三个命令的参数都是「[档位] [活动ID] [服务器]」，但活动 ID 与服务器都可省略。
解析方式是先把开头的纯数字当活动 ID 摘掉，剩下的第一个非数字当服务器，
这样 `ycx 1000`、`ycx 1000 177`、`ycx 1000 jp`、`ycx 1000 177 jp` 都能正确解析。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .. import api, user
from .. import constants as const
from . import Ctx, register

if TYPE_CHECKING:
    from tsugu_api_core._typing import ServerId


async def _resolve_event_and_server(
    ctx: Ctx, rest: list[str]
) -> tuple[int | None, ServerId | None] | None:
    """从剩余参数里解析出 (活动ID, 服务器ID)。解析失败时已回复错误并返回 None。"""
    rest = list(rest)

    event_id: int | None = None
    if rest and rest[0].isdigit():
        event_id = int(rest.pop(0))

    server: ServerId | None = None
    if rest:
        try:
            server = await api.resolve_server(rest[0])
        except ValueError as exc:
            await ctx.reply_error(str(exc))
            return None

    return event_id, server


@register("cutoff")
async def handle_cutoff(ctx: Ctx) -> None:
    if not ctx.args or not ctx.args[0].isdigit():
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    tier = int(ctx.args[0])
    parsed = await _resolve_event_and_server(ctx, ctx.args[1:])
    if parsed is None:
        return
    event_id, server = parsed

    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(
        await api.cutoff_detail(server or tsugu_user.main_server, tier, event_id)
    )


@register("cutoff_all")
async def handle_cutoff_all(ctx: Ctx) -> None:
    parsed = await _resolve_event_and_server(ctx, ctx.args)
    if parsed is None:
        return
    event_id, server = parsed

    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(await api.cutoff_all(server or tsugu_user.main_server, event_id))


@register("cutoff_history")
async def handle_cutoff_history(ctx: Ctx) -> None:
    if not ctx.args or not ctx.args[0].isdigit():
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    tier = int(ctx.args[0])
    parsed = await _resolve_event_and_server(ctx, ctx.args[1:])
    if parsed is None:
        return
    event_id, server = parsed

    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(
        await api.cutoff_history(server or tsugu_user.main_server, tier, event_id)
    )
```

- [ ] **Step 3: 写 commands/player.py**

```python
"""查玩家。"""

from __future__ import annotations

from .. import api, user
from .. import constants as const
from . import Ctx, register


@register("search_player")
async def handle_search_player(ctx: Ctx) -> None:
    if not ctx.args or not ctx.args[0].isdigit():
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    player_id = int(ctx.args[0])

    server = None
    if len(ctx.args) > 1:
        try:
            server = await api.resolve_server(ctx.args[1])
        except ValueError as exc:
            await ctx.reply_error(str(exc))
            return

    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply(
        await api.search_player(player_id, server or tsugu_user.main_server)
    )
```

- [ ] **Step 4: 写 commands/station.py**

```python
"""车牌查询：ycm。"""

from __future__ import annotations

from .. import api
from . import Ctx, register


@register("ycm")
async def handle_ycm(ctx: Ctx) -> None:
    try:
        rooms = await api.query_all_rooms()
    except api.UserDataError as exc:
        await ctx.reply_error(str(exc))
        return

    if ctx.args:
        keyword = " ".join(ctx.args)
        rooms = [room for room in rooms if keyword in room.get("rawMessage", "")]
        if not rooms:
            await ctx.reply_text(f"没有找到包含 {keyword} 的房间")
            return

    # 房间列表为空时后端自己会返回提示文本，这里不用特殊处理
    await ctx.reply(await api.render_room_list(rooms))
```

- [ ] **Step 5: 验证这批命令已注册且工程能启动**

```bash
cd /Users/tano/Documents/GitHub/personal/kasumi_bot
.venv/bin/python "$CLAUDE_JOB_DIR/tmp/boot_probe.py" 20 "$CLAUDE_JOB_DIR/tmp/boot.log"
tail -30 "$CLAUDE_JOB_DIR/tmp/boot.log"
grep -h "@register" src/plugins/tsugu/commands/*.py | wc -l
```

Expected: `nb run` 无报错；累计注册数达到 19（Task 7 的 5 + Task 8 的 7 + Task 9 的 7）。Task 10 会再加 11 个，最终 30。

- [ ] **Step 6: 静态检查并提交**

```bash
.venv/bin/ruff check src/ && .venv/bin/ruff format src/ && .venv/bin/pyright src/
git add -A
git commit -m "feat: 新增查活动、预测线、查玩家与车站命令"
```

---

### Task 10: 用户设置命令与帮助

**Files:**
- Create: `src/plugins/tsugu/commands/settings.py`
- Create: `src/plugins/tsugu/commands/help.py`

**Interfaces:**
- Consumes: `commands.Ctx`、`commands.register`、`api`、`user`、`constants`
- Produces: 向 `HANDLERS` 注册 `bind_player`、`bind_reply`、`unbind_player`、`main_server`、`display_servers`、`player_status`、`player_list`、`player_index`、`open_forward`、`close_forward`、`help`

- [ ] **Step 1: 写 commands/settings.py**

```python
"""用户设置类命令：绑定、解绑、主服务器、显示服务器、玩家状态、车牌转发。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .. import api, user
from .. import constants as const
from . import Ctx, register

if TYPE_CHECKING:
    from tsugu_api_core._typing import ServerId


@register("bind_player")
async def handle_bind_player(ctx: Ctx) -> None:
    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)

    if ctx.args:
        try:
            server = await api.resolve_server(ctx.args[0])
        except ValueError as exc:
            await ctx.reply_error(str(exc))
            return
    else:
        server = tsugu_user.main_server

    try:
        code = await api.request_bind_code(ctx.user_id)
    except api.UserDataError as exc:
        await ctx.reply_error(str(exc))
        return

    user.pending[ctx.user_id] = user.PendingBind(action="bind", server=server)
    await ctx.reply_text(user.build_bind_prompt(server, code))


@register("bind_reply")
async def handle_bind_reply(ctx: Ctx) -> None:
    """绑定流程的第二步。由分派器在发现待处理流程时调用。

    分派器只 `get` 不 `pop`，所以**只有真正成功时**才在这里清掉待处理状态；
    中途失败（玩家 ID 不合法、验证码没对上）都保留状态让用户重试，
    直到成功或超过 tsugu_bind_timeout。
    """
    pending = ctx.pending
    if pending is None:
        return

    # 解绑不需要玩家 ID，用户发任意消息即可
    if pending.action == "unbind":
        if pending.player_id is None:
            return
        try:
            message = await api.verify_bind(
                ctx.user_id, pending.server, pending.player_id, "unbind"
            )
        except api.UserDataError as exc:
            await ctx.reply_error(str(exc))
            return
        user.pending.pop(ctx.user_id, None)
        await ctx.reply_text(message)
        return

    player_id_text = ctx.args[0].strip() if ctx.args else ""
    if not player_id_text.isdigit():
        await ctx.reply_text(const.ERR_PLAYER_ID_INVALID)
        return

    player_id = int(player_id_text)
    try:
        await api.verify_bind(ctx.user_id, pending.server, player_id, "bind")
    except api.UserDataError as exc:
        await ctx.reply_error(str(exc))
        return

    user.pending.pop(ctx.user_id, None)
    await ctx.matcher.send(
        f"绑定 {user.server_name(pending.server)} 玩家 {player_id} 成功，"
        "正在生成玩家状态图片"
    )
    await ctx.reply(await api.search_player(player_id, pending.server))


@register("unbind_player")
async def handle_unbind_player(ctx: Ctx) -> None:
    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)

    if ctx.args:
        try:
            server = await api.resolve_server(ctx.args[0])
        except ValueError as exc:
            await ctx.reply_error(str(exc))
            return
    else:
        server = tsugu_user.main_server

    try:
        player = user.pick_player(tsugu_user, server=server)
    except ValueError as exc:
        await ctx.reply_error(str(exc))
        return

    try:
        code = await api.request_bind_code(ctx.user_id)
    except api.UserDataError as exc:
        await ctx.reply_error(str(exc))
        return

    player_id = player["playerId"]
    user.pending[ctx.user_id] = user.PendingBind(
        action="unbind", server=server, player_id=player_id
    )
    await ctx.reply_text(
        f"正在解除绑定来自 {user.server_name(server)} 账号 玩家ID: {player_id} \n"
        "请将你的\n"
        "评论(个性签名)\n"
        "或者\n"
        "你的当前使用的卡组的卡组名(乐队编队名称)\n"
        "改为以下数字后，发送任意消息继续\n"
        f"{code}"
    )


@register("main_server")
async def handle_main_server(ctx: Ctx) -> None:
    if not ctx.args:
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    try:
        server = await api.resolve_server(ctx.args[0])
    except ValueError as exc:
        await ctx.reply_error(str(exc))
        return

    error = await api.change_user(ctx.user_id, {"mainServer": server})
    if error:
        await ctx.reply_error(error)
        return
    await ctx.reply_text(f"已切换到{user.server_name(server)}模式")


@register("display_servers")
async def handle_display_servers(ctx: Ctx) -> None:
    if not ctx.args:
        await ctx.reply_error("错误: 请指定至少一个服务器")
        return

    servers: list[ServerId] = []
    for name in ctx.args:
        try:
            server = await api.resolve_server(name)
        except ValueError:
            await ctx.reply_error("错误: 指定了不存在的服务器")
            return
        if server in servers:
            await ctx.reply_error("错误: 指定了重复的服务器")
            return
        servers.append(server)

    error = await api.change_user(ctx.user_id, {"displayedServerList": servers})
    if error:
        await ctx.reply_error(error)
        return
    await ctx.reply_text(
        "成功切换默认显示服务器顺序: "
        + ", ".join(user.server_name(server) for server in servers)
    )


@register("player_status")
async def handle_player_status(ctx: Ctx) -> None:
    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)

    index: int | None = None
    server: ServerId | None = None

    if ctx.args:
        if ctx.args[0].isdigit():
            index = int(ctx.args[0])
            if len(ctx.args) > 1:
                try:
                    server = await api.resolve_server(ctx.args[1])
                except ValueError as exc:
                    await ctx.reply_error(str(exc))
                    return
        else:
            try:
                server = await api.resolve_server(ctx.args[0])
            except ValueError as exc:
                await ctx.reply_error(str(exc))
                return

    try:
        player = user.pick_player(tsugu_user, server=server, index=index)
    except ValueError as exc:
        await ctx.reply_error(str(exc))
        return

    await ctx.reply(await api.search_player(player["playerId"], player["server"]))


@register("player_list")
async def handle_player_list(ctx: Ctx) -> None:
    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    await ctx.reply_text(user.build_player_list_text(tsugu_user))


@register("player_index")
async def handle_player_index(ctx: Ctx) -> None:
    if not ctx.args or not ctx.args[0].isdigit():
        await ctx.reply_error(const.incomplete_cmd_text(ctx.head))
        return

    index = int(ctx.args[0])
    tsugu_user = await user.load_user_or_finish(ctx.matcher, ctx.user_id)
    if index < 1 or index > len(tsugu_user.user_player_list):
        await ctx.reply_error(const.ERR_INDEX_INVALID)
        return

    error = await api.change_user(ctx.user_id, {"userPlayerIndex": index - 1})
    if error:
        await ctx.reply_error(error)
        return
    await ctx.reply_text(f"已切换至绑定信息ID: {index}")


async def _toggle_forward(ctx: Ctx, *, enabled: bool) -> None:
    error = await api.change_user(ctx.user_id, {"shareRoomNumber": enabled})
    if error:
        await ctx.reply_error(error)
        return
    await ctx.reply_text("已开启车牌转发" if enabled else "已关闭车牌转发")


@register("open_forward")
async def handle_open_forward(ctx: Ctx) -> None:
    await _toggle_forward(ctx, enabled=True)


@register("close_forward")
async def handle_close_forward(ctx: Ctx) -> None:
    await _toggle_forward(ctx, enabled=False)
```

- [ ] **Step 2: 写 commands/help.py**

`USAGES` 的每一项第一行是签名、第二行是一句话说明、之后是示例。`help` 总表只取第一行与第二行。

```python
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
```

- [ ] **Step 3: 验证全部命令注册齐全**

```bash
cd /Users/tano/Documents/GitHub/personal/kasumi_bot
.venv/bin/python "$CLAUDE_JOB_DIR/tmp/boot_probe.py" 20 "$CLAUDE_JOB_DIR/tmp/boot.log"
tail -30 "$CLAUDE_JOB_DIR/tmp/boot.log"
.venv/bin/python - <<'PY'
import sys
sys.path.insert(0, "src/plugins")

import nonebot

# tsugu/__init__.py 在 import 时就会调用 get_plugin_config，必须先初始化 NoneBot
nonebot.init()
from tsugu import constants as K

# help.py 的 USAGES / HELP_ORDER 必须覆盖每一个非 bind_reply 的命令
sys.path.insert(0, "src/plugins/tsugu/commands")
src = open("src/plugins/tsugu/commands/help.py", encoding="utf-8").read()
import re
covered = set(re.findall(r'^    "([a-z_]+)":', src, re.M))
covered |= set(re.findall(r'^    "([a-z_]+)",$', src, re.M))

commands = {cmd for _, cmd in K.COMMAND_HEADS}
missing = commands - covered - {"bind_reply"}
assert not missing, f"help 里缺少这些命令: {sorted(missing)}"
print("help 覆盖全部", len(commands), "个命令")
PY
```

Expected: `nb run` 无报错；打印 `help 覆盖全部 30 个命令`。若报 missing，把缺的命令补进 `USAGES` 与 `HELP_ORDER`。

- [ ] **Step 4: 静态检查并提交**

```bash
.venv/bin/ruff check src/ && .venv/bin/ruff format src/ && .venv/bin/pyright src/
git add -A
git commit -m "feat: 新增用户设置命令与帮助系统"
```

---

### Task 11: 端到端验证与收尾

**Files:**
- Modify: `CLAUDE.md`（更新架构说明、命令、依赖）

**Interfaces:**
- Consumes: 前十个任务的全部产出
- Produces: 一个通过全部静态检查与假事件验证、文档与实现一致的仓库

- [ ] **Step 1: 全量静态检查**

```bash
cd /Users/tano/Documents/GitHub/personal/kasumi_bot
.venv/bin/ruff check src/ && echo "ruff check 通过"
.venv/bin/ruff format --check src/ && echo "ruff format 通过"
.venv/bin/pyright src/ && echo "pyright 通过"
```

Expected: 三条都打印通过。有报错就修，不要用 `# type: ignore` 掩盖——除非是第三方库的类型缺失，那种情况在那一行加具体说明的 ignore。

- [ ] **Step 2: 端到端启动验证**

```bash
cd /Users/tano/Documents/GitHub/personal/kasumi_bot
rm -rf data
.venv/bin/python "$CLAUDE_JOB_DIR/tmp/boot_probe.py" 25 "$CLAUDE_JOB_DIR/tmp/boot.log"
tail -40 "$CLAUDE_JOB_DIR/tmp/boot.log"
echo "--- 检查 ---"
grep -q 'Succeeded to load plugin "tsugu"' "$CLAUDE_JOB_DIR/tmp/boot.log" && echo "插件加载 OK"
! grep -qiE "traceback|error|failed to" "$CLAUDE_JOB_DIR/tmp/boot.log" && echo "无异常 OK"
.venv/bin/python -c "
import sqlite3
tables = sorted(r[0] for r in sqlite3.connect('data/db.sqlite3').execute(
    \"select name from sqlite_master where type='table'\"))
assert tables == ['alembic_version', 'tsugu_group_settings'], tables
print('建表 OK:', tables)
"
```

Expected: 三行 OK，无 Traceback。

- [ ] **Step 3: 用假事件走一遍完整分派路径**

写到 `$CLAUDE_JOB_DIR/tmp/probe_dispatch.py`。这条探针把 `__init__.py` 里分派器的决策逻辑原样复现一遍，覆盖规格第 12 节列出的全部路径：

```python
import sys

sys.path.insert(0, "src/plugins")

import nonebot

# tsugu/__init__.py 在 import 时就会调用 get_plugin_config，必须先初始化 NoneBot
nonebot.init()

from tsugu import constants as const
from tsugu.rule import apply_shortcut, build_head_table, match_car, match_command, normalize

TABLE = build_head_table(const.COMMAND_HEADS)


def plan(text: str, no_space: bool = False):
    """复现分派器在「无待处理绑定流程」时的决策顺序。"""
    text = normalize(text)
    car = match_car(text, const.CAR_KEYWORDS, const.FAKE_KEYWORDS)
    if car is not None:
        return ("car", car[0])
    matched = match_command(apply_shortcut(text), TABLE, no_space=no_space)
    if matched is None:
        return None
    return (matched.command, matched.args)


# @bot 剥离后（extract_plain_text 的产物）
assert plan(" 查卡 1399") == ("search_card", ["1399"])
assert plan(" 查卡 绿 tsugu") == ("search_card", ["绿", "tsugu"])

# shortcut
assert plan("日服模式") == ("main_server", ["日服"])
assert plan("国服玩家状态") == ("player_status", ["国服"])

# 车牌优先于命令
assert plan("123456 大分e") == ("car", 123456)
assert plan("123456 雀魂") is None

# 无空格开关
assert plan("查卡947", no_space=False) is None
assert plan("查卡947", no_space=True) == ("search_card", ["947"])

# 帮助与抽卡开关
assert plan("help") == ("help", [])
assert plan("开启抽卡") == ("gacha_on", [])
assert plan("抽卡 off") == ("gacha_switch", ["off"])

# 长命令头优先
assert plan("抽卡模拟 300") == ("gacha_simulate", ["300"])
assert plan("查卡面 1399") == ("card_illustration", ["1399"])
assert plan("玩家状态列表") == ("player_list", [])

# 无参数命令
assert plan("ycm") == ("ycm", [])
assert plan("玩家状态") == ("player_status", [])

# 完全不认识的消息不应误触发
assert plan("今天天气不错") is None
assert plan("") is None

print("分派路径探针全部通过")
```

- [ ] **Step 4: 运行分派探针**

```bash
cd /Users/tano/Documents/GitHub/personal/kasumi_bot
.venv/bin/python "$CLAUDE_JOB_DIR/tmp/probe_dispatch.py"
```

Expected: 打印 `分派路径探针全部通过`。

- [ ] **Step 5: 用桩 matcher 覆盖实际发送路径**

Task 4 的探针只覆盖了 `split_messages` / `build_message` 两个纯函数，`send_result`
的发送循环与 @ 前缀拼接一直没有运行时覆盖——而它是所有命令最终都会走的那条路。
这里用桩 matcher 补上。

写到 `$CLAUDE_JOB_DIR/tmp/probe_send.py`：

```python
import asyncio
import sys
from base64 import b64encode

sys.path.insert(0, "src/plugins")

import nonebot

nonebot.init()

from nonebot.adapters.qq import Message

from tsugu.sender import send_result


class StubMatcher:
    """只记录收到了什么，不碰网络。"""

    def __init__(self) -> None:
        self.sent: list[Message] = []

    async def send(self, message: Message) -> None:
        self.sent.append(message)


PNG = b"\x89PNG\r\n\x1a\n" + b"fake"
ITEMS = [
    {"type": "string", "string": "第一段"},
    {"type": "base64", "string": b64encode(PNG).decode()},
]


async def main() -> None:
    # 不带 @：文本与图片各一条，顺序保持
    matcher = StubMatcher()
    await send_result(matcher, ITEMS, limit=5)
    assert len(matcher.sent) == 2, matcher.sent
    assert matcher.sent[0][0].type == "text", matcher.sent[0]
    assert matcher.sent[1][0].type == "file_image", matcher.sent[1]

    # 带 @：只加在第一条上
    matcher = StubMatcher()
    await send_result(matcher, ITEMS, limit=5, at_user_id="USER_OPENID")
    assert len(matcher.sent) == 2
    assert matcher.sent[0][0].type == "mention_user", matcher.sent[0]
    assert matcher.sent[1][0].type == "file_image", "第二条不该带 @"

    # 空响应不发任何消息
    matcher = StubMatcher()
    await send_result(matcher, [], limit=5)
    assert matcher.sent == []

    # 超限时按 limit 截断
    matcher = StubMatcher()
    await send_result(matcher, [ITEMS[1]] * 8, limit=5)
    assert len(matcher.sent) == 5, len(matcher.sent)
    assert matcher.sent[-1][0].data["text"].startswith("结果过长"), matcher.sent[-1]

    print("send_result 桩测通过")


asyncio.run(main())
```

运行：

```bash
cd /Users/tano/Documents/GitHub/personal/kasumi_bot
.venv/bin/python "$CLAUDE_JOB_DIR/tmp/probe_send.py"
```

Expected: 打印 `send_result 桩测通过`。

- [ ] **Step 6: 对公共后端跑一次真实查询回归**

```bash
cd /Users/tano/Documents/GitHub/personal/kasumi_bot
.venv/bin/python "$CLAUDE_JOB_DIR/tmp/probe_api.py"
```

Expected: 打印 `api 探针全部通过`（Task 5 写的那个探针，此时应当仍然通过）。

- [ ] **Step 7: 更新 CLAUDE.md**

把「Project Overview」「Existing plugins」「Adding a New Plugin」等段落改成现状：

- 概述：说明这是 Tsugu BanGDream Bot 的 QQ 官方 Bot 前端，数据与渲染来自 Tsugu 公共后端。
- 架构：加上「QQ 官方 Bot ← WebSocket → nonebot-adapter-qq → NoneBot2 → src/plugins/tsugu/ → httpx → Tsugu 后端」这条链路，并说明**为什么不使用 `on_command`**（群里 `@bot` 会让 `message[0]` 成为 `MentionUser`，`TrieRule` 不匹配）。
- 现有插件：`tsugu`（唯一插件），并逐个说明 `rule.py` / `sender.py` / `api.py` / `user.py` / `db.py` / `commands/` 的职责。
- 环境文件：更新 `.env` 的实际内容，特别标注 `DRIVER` 必须包含 `~websockets`，否则 QQ 适配器启动即失败。
- 常见命令：`ruff check src/`、`ruff format src/`、`pyright src/`、`nb run --reload`。
- 提到设计规格与实现计划的位置：`docs/superpowers/specs/` 与 `docs/superpowers/plans/`。

- [ ] **Step 8: 最终提交**

```bash
git add -A
git commit -m "docs: 更新 CLAUDE.md 以反映 Tsugu 改造后的架构"
```

- [ ] **Step 9: 交付说明**

向用户报告：
- 分支名与提交列表
- `.env.prod` 需要填的变量（`QQ_BOT_ID` / `QQ_BOT_TOKEN` / `QQ_BOT_SECRET`），以及 `DRIVER` 必须带 `~websockets`
- 真机联调待办：把 Bot 接入 QQ 官方沙箱，逐条验证规格 5.1 / 5.2 / 5.3 的命令
- 已知限制（规格第 13 节）：群聊车牌收不到、单次回复 5 条上限、依赖公共后端、与官方 Tsugu 共用 `red` 命名空间、群级抽卡开关无权限校验

---

## 完成标准

全部满足才算完成：

1. `ruff check src/`、`ruff format --check src/`、`pyright src/` 均无输出。
2. `nb run` 启动无 Traceback，日志有 `Succeeded to load plugin "tsugu" from "src.plugins.tsugu"`。
3. `data/db.sqlite3` 恰好含 `alembic_version` 与 `tsugu_group_settings` 两张表。
4. `probe_rule.py`、`probe_sender.py`、`probe_user.py`、`probe_event.py`、`probe_dispatch.py`、`probe_api.py` 全部通过。
5. `src/plugins/tsugu/commands/` 下累计 30 个 `@register`（含 `bind_reply`，`bind_reply` 不出现在 help 里）。
6. `CLAUDE.md` 反映改造后的架构与命令。
7. 每个提交都是单行信息、无正文、无 `Co-Authored-By`、无任何 Claude 字样。
