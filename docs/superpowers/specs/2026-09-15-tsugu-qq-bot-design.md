# kasumi_bot → Tsugu QQ 官方 Bot 改造设计

日期：2026-09-15
状态：已确认，待实现

## 1. 背景与目标

`kasumi_bot` 目前是一个演示性质的 NoneBot2 + QQ 官方适配器项目，只有 `bangdream`（问答）、`live`（演出 RSS）、`proactive`（主动消息）、`basic`、`test` 五个自定义插件，代码合计约 690 行。

目标是把它改造成功能与 [Tsugu BanGDream Bot](https://github.com/Yamamoto-2/tsugu-bangdream-bot) 一致的 QQ 官方机器人：保留 QQ 官方 Bot 的交互方式（被动消息、`@` 触发、富媒体图片上传），但命令集、参数语义、返回内容、用户数据模型全部对齐 Tsugu。

### 1.1 关键架构前提

Tsugu 是**前后端分离**的：

- **前端**负责命令解析、用户数据交互、把结果渲染成消息。
- **后端**（Node.js + skia-canvas）负责全部数据查询与图片渲染，数据源为 Bestdori / BandoriStation / HHWX。后端通过 HTTP 暴露一组无鉴权的公开 JSON API，统一返回 `[{"type": "string"|"base64", "string": "..."}]`。

因此**本项目的定位是 Tsugu 的一个新前端**，复用 Tsugu 公共后端，不重新实现渲染。这样能真正做到「功能完全一致」，且用户数据与官方 Tsugu 各项客户端互通。

### 1.2 已实测确认的事实

在 `http://tsugubot.com:8080`（Tsugu 公共后端）上实测：

| 探测 | 结果 | 结论 |
|---|---|---|
| `POST /fuzzySearch {"text":"绿 tsugu"}` | `{"status":"success","data":{"attribute":["pure"],"characterId":[10]}}` | 查询 API 连通，模糊搜索符合预期 |
| `POST /user/getUserData {}` | HTTP 400 `参数错误`（字段校验失败） | **`/user/*` 路由已挂载**，后端 `LOCAL_DB=true` |
| `GET /station/queryAllRoom` | HTTP 200 `{"status":"success","data":[]}` | **`/station/*` 路由已挂载** |
| `POST /searchSong {"displayedServerList":[3,1],"text":"1","compress":true}` | 单条 `base64`，长度 423368 字符（≈310 KB） | 图片体积在 QQ 富媒体限制内 |

### 1.3 已实测确认的适配器行为

- `nonebot-adapter-qq` 的 `Bot.send(event, message)` **已自动处理 QQ 被动消息**：自动填 `msg_id=event.id`，并对同一事件内每次发送自增 `event._reply_seq` 作为 `msg_seq`，还会从 `message_scene.ext` 提取 `msg_ref_id` 实现引用。**无需自写被动消息层。**
- `Message.extract_plain_text()` 会剥掉 `@bot`（`MentionUser` 段不是 `Text` 段），但会保留前导空格：`"<@!123> 查卡 1399"` → `" 查卡 1399"`。需要 `.strip()`。
- **`on_command` 无法用于 QQ 群消息**：`nonebot.rule.TrieRule.get_value` 只检查 `message[0]`，而 `@bot 查卡 1399` 的第一个 segment 是 `MentionUser`，`is_text()` 为 `False`，命令匹配直接失败。这必须由自定义触发层解决。
- **当前 `.env` 的驱动配置是坏的**：`DRIVER=~fastapi+~httpx` 解析出的 `CombinedDriver` 不满足 `WebSocketClientMixin`（实测 `isinstance` 为 `False`），而 `qq_config.py` 设置了 `use_websocket=True`，QQ 适配器在 `adapter.py:74-80` 会直接抛 `QQ Adapter need a WebSocketClient Driver to work.`。实测 `~fastapi+~httpx+~websockets` 才同时满足 `WebSocketClientMixin` 与 `HTTPClientMixin`。本次一并修复。

## 2. 范围

### 2.1 做

- 完整复刻 Tsugu 主线的命令集（含别名与两个 shortcut 正则）。
- 用户数据走 Tsugu 用户数据 API，`platform="red"`。
- QQ 官方 Bot 特有的触发与发送适配。
- 车牌自动转发（消息级监听）。
- 群级抽卡开关，存本地 SQLite。

### 2.2 不做

- 单元测试、集成测试、路由守卫、权限系统（明确要求精简）。
- 用本地库存用户数据。绑定、主服务器、显示服务器、车牌开关等全部托管在 Tsugu 后端（见 6.1），本地库只存群级设置这一张表（见 6.5）。
- 自建 Tsugu 后端（只通过配置项支持切换地址）。
- article API（`/eventPreview/*`、`/eventReport/*`）：Tsugu 前端本身也没有暴露对应命令。
- `tsugu_swc`（试验性的频道总开关）：mainline 里就标注为试验性，且交互方式（`tsugu_swc off @bot`）在 QQ 官方 Bot 下很别扭。
- 保留任何现有插件。`src/plugins/` 下 `bangdream`、`live`、`proactive`、`basic`、`test` 全部删除。

## 3. 架构与数据流

```
QQ 官方服务器
   │  WebSocket
   ▼
nonebot-adapter-qq   →  GroupAtMessageCreateEvent / C2CMessageCreateEvent
   ▼
NoneBot2 Core
   ▼
src/plugins/tsugu/
   ├─ rule.py     触发层：剥 @、命令头 trie、shortcut 正则、车牌正则
   ├─ commands/   命令实现
   ├─ user.py     用户数据 + 绑定/解绑流程
   ├─ sender.py   [{"type","string"}] → QQ Message，多图拆分与条数上限
   ├─ api.py      tsugu-api-python 封装 + 错误文案映射
   ├─ car.py      车牌自动转发
   ├─ db.py       群级设置（本地 SQLite）
   └─ config.py   Pydantic 配置
   │
   ├─ httpx POST JSON ──────────────► Tsugu 后端  http://tsugubot.com:8080
   │                                     ├─ /searchCard /searchSong /cutoffDetail …  查询 API
   │                                     ├─ /user/*     用户数据 API
   │                                     └─ /station/*  车站 API
   │
   └─ SQLAlchemy ────────────────────► data/db.sqlite3（仅 tsugu_group_settings 一张表）
```

**用户数据不在本地**：以 `platform="red"` + QQ openid 为键存在 Tsugu 后端。本地 SQLite 只承载群级设置。

## 4. 触发层（`rule.py`）

QQ 群里 Bot 只能收到 `@` 了它的消息；私聊里能收到全部消息。因此需要一个统一的规范化入口，而非 `on_command`。

### 4.1 规范化

```
text = event.get_message().extract_plain_text().strip()
```

`extract_plain_text()` 已剥掉 `@bot` 与引用标签，`.strip()` 去掉前导空格。

### 4.2 分派顺序

1. **车牌识别**（仅消息级监听器，优先级最高）
   正则 `^(\d{5,6})(.*)$`；命中后要求：
   - 用户 `shareRoomNumber` 为 `true`
   - `rest` 小写后包含至少一个 car 关键词
   - `rest` 小写后不包含任何 fake 关键词

   群聊中非 `@` 消息收不到，此逻辑自然不触发；私聊中正常工作。逻辑完整保留，将来若获得全量消息权限即自动生效。

2. **Shortcut 正则**（与 mainline Tsugu 一致）
   - `^(.+服)模式$` → 改写为 `主服务器 $1`（例：`日服模式`）
   - `^(.+服)玩家状态$` → 改写为 `玩家状态 $1`（例：`国服玩家状态`）

3. **命令头匹配**
   自建 trie，注册全部命令头与别名。匹配规则：
   - 默认：命令头之后必须是空白（或字符串结束），`cmd_args = text[len(head):].lstrip()`
   - `tsugu_no_space=true` 时：允许命令头与参数直接相连（`查卡947`）

   按命令头**长度降序**匹配，避免 `查卡` 抢先命中 `查卡面`。

### 4.3 参数解析约定

- 参数以空白切分。
- 函数签名里的 `<x>` 为必填，`[x]` 为可选。
- `<word...>` 表示把剩余全部参数用单个空格拼回字符串，**原样**交给后端做模糊搜索（`查卡 绿 tsugu` → `text="绿 tsugu"`）。
- 必填参数缺失或类型不符时，回复下列两行文本（与 mainline Tsugu 的 Koishi 实现一致）：

  ```
  错误: 指令不完整
  使用以下指令以查看帮助:
    help <命令名>
  ```

- 服务器名参数解析顺序：先本地表（`jp/en/tw/cn/kr`、`日服/国际服/台服/国服/韩服`、`0`-`4`），未命中再调 `fuzzy_search(text)["server"][0]`；仍失败报 `错误: 服务器名未能匹配任何服务器`。
- 难度参数解析：先本地表（`ez/easy/简单`→0、`nm/normal/普通`→1、`hd/hard/困难`→2、`ex/expert/专家`→3、`sp/special/特殊`→4），未命中再调 `fuzzy_search`；失败报 `错误: 难度名未能匹配任何难度`。
- `-m` 这类选项从参数列表中**任意位置**摘除，剩余参数按位置顺序解析。仅 `查试炼` 使用 `-m`。

## 5. 命令清单

服务器名统一记作 `<服>`。除特别标注外，所有命令结果都是「图片 + 可能的文本」，由 `sender.py` 统一处理。

### 5.1 查询类

| 命令头（别名） | 参数 | 后端调用 |
|---|---|---|
| `查卡`（`查卡牌`） | `<词...>` | `search_card(displayed_server_list, text=词)` |
| `查卡面`（`查卡插画`、`查插画`） | `<卡ID>` | `get_card_illustration(card_id)` |
| `查角色` | `<词...>` | `search_character(displayed_server_list, text=词)` |
| `查活动` | `<词...>` | `search_event(displayed_server_list, text=词)` |
| `查卡池` | `<卡池ID>` | `search_gacha(displayed_server_list, gacha_id)` |
| `查曲` | `<词...>` | `search_song(displayed_server_list, text=词)` |
| `查谱面` | `<曲ID> [难度]` | `song_chart(displayed_server_list, song_id, difficulty_id)`，难度默认 `expert`(3) |
| `随机曲`（`随机`） | `[词...]` | `song_random(main_server, text=词)` |
| `查询分数表`（`查分数表`、`查询分数榜`、`查分数榜`） | `[服]` | `song_meta(displayed_server_list, main_server)` |
| `查试炼`（`查stage`、`查舞台`、`查festival`、`查5v5`） | `[活动ID] [-m]` | `event_stage(main_server, event_id, meta)` |
| `查玩家`（`查询玩家`） | `<玩家ID> [服]` | `search_player(player_id, main_server)` |
| `抽卡模拟` | `<次数> [卡池ID]` | `gacha_simulate(main_server, times, gacha_id)` |
| `ycx` | `<档位> [活动ID] [服]` | `cutoff_detail(main_server, tier, event_id)` |
| `ycxall`（`myycx`） | `[活动ID] [服]` | `cutoff_all(main_server, event_id)` |
| `lsycx` | `<档位> [活动ID] [服]` | `cutoff_list_of_recent_event(main_server, tier, event_id)` |
| `ycm`（`有车吗`、`车来`） | `[关键词...]` | `station_query_all_room()` → 关键词过滤 → `room_list(rooms)` |

`displayedServerList` 取自用户数据的 `displayedServerList`；`mainServer` 取自 `mainServer`。带 `[服]` 参数的命令，显式指定时覆盖 `mainServer`。

**与实际代码对齐的两处说明**（以代码为准，而非文档或示例）：

1. `抽卡模拟` 的 `次数` 是**必填**。mainline Tsugu 的 `.example()` 写着「抽卡模拟:模拟抽卡10次」，但 `.action()` 在 `times == undefined` 时直接返回 `错误: 指令不完整`。本实现跟随代码行为。
2. `查谱面` 的难度默认值为 `expert`(3)。

### 5.2 用户设置类

| 命令头（别名） | 参数 | 行为 | 成功回复 |
|---|---|---|---|
| `绑定玩家` | `[服]` | 两段式绑定流程，见 6.2 | 见 6.2 |
| `解除绑定`（`解绑玩家`） | `[服]` | 两段式解绑流程，见 6.2 | 后端返回文本 |
| `主服务器`（`服务器模式`、`切换服务器`） | `<服>` | `change_user_data({"mainServer": 服})` | `已切换到{服名}模式` |
| `设置显示服务器`（`默认服务器`、`设置默认服务器`） | `<服...>` | 见下方校验规则 | `成功切换默认显示服务器顺序: {服名, 服名}` |
| `玩家状态` | `[序号] [服]` | 见 6.3 | 玩家状态图 |
| `玩家状态列表`（`玩家列表`、`玩家信息列表`） | — | 纯文本，见 6.4 | 见 6.4 |
| `玩家默认ID`（`默认玩家ID`、`默认玩家`、`玩家ID`） | `<序号>` | 见下方校验规则 | `已切换至绑定信息ID: {序号}` |
| `开启车牌转发` | — | `change_user_data({"shareRoomNumber": True})` | `已开启车牌转发` |
| `关闭车牌转发` | — | `change_user_data({"shareRoomNumber": False})` | `已关闭车牌转发` |

`设置显示服务器` 的校验规则（按顺序，命中即返回）：服务器名为空 → `错误: 请指定至少一个服务器`；出现重复 → `错误: 指定了重复的服务器`；某个名字解析不出服务器 → `错误: 指定了不存在的服务器`。

`玩家默认ID` 的校验规则：先读用户数据，`序号 < 1` 或 `序号 > len(userPlayerList)` → `错误: 无效的绑定信息ID`；否则写入 `userPlayerIndex = 序号 - 1`。

所有 `change_user_data` 返回 `{"status": "failed"}` 时，把 `data` 字段原样回给用户。

### 5.3 群级设置

只有一项：本群抽卡开关。设置存在本地 SQLite，按 `group_openid` 索引。

| 命令头（别名） | 参数 | 行为 | 回复 |
|---|---|---|---|
| `抽卡` | `<on\|off\|开启\|关闭>` | 写入本群开关 | `开启成功` / `关闭成功` / `无效指令` |
| `开启抽卡` | — | 等价于 `抽卡 on` | `开启成功` |
| `关闭抽卡` | — | 等价于 `抽卡 off` | `关闭成功` |

- 只对群消息有效。C2C（私聊）没有群概念，抽卡始终可用，收到这三个命令时回复 `该指令仅在群聊中可用`。
- `抽卡模拟` 在执行前查本群设置，关闭时直接回复 `抽卡功能已关闭`，不调后端。
- 命令头匹配按长度降序，`抽卡模拟` 会先于 `抽卡` 命中，两者不冲突。
- **不做权限校验**：QQ 官方 Bot 的群消息事件（`GroupAtMessageCreateEvent`）不携带成员角色字段（只有频道/guild 事件才有 `roles`），无法判断发送者是否为群管理员。因此任何群成员都可开关。mainline 的权限校验依赖 Koishi 的 `session.authority`/`roles`，QQ 官方平台没有对等物。若日后要收紧，可在这一处加 `SUPERUSERS` 白名单判断。

### 5.4 帮助

`help` / `帮助` `[命令名]`。无参数时列出全部命令头与一行说明；带命令名时输出该命令的完整用法、参数与示例。帮助文本集中在 `commands/help.py` 的一张表里，命令注册与帮助共用同一份元数据，避免两处漂移。

## 6. 用户数据

### 6.1 模型

```python
{
  "userId": str,
  "platform": "red",
  "mainServer": 3,                     # 国服
  "displayedServerList": [3, 0],       # 国服, 日服（实测公共后端新建用户即为 [3, 0]）
  "shareRoomNumber": True,
  "userPlayerIndex": 0,
  "userPlayerList": [{"playerId": int, "server": int}, ...]
}
```

读取：`get_user_data(platform, user_id)["data"]`（后端对不存在的用户自动创建）。
写入：`change_user_data(platform, user_id, update)`。后端**只接受** `mainServer`、`displayedServerList`、`shareRoomNumber`、`userPlayerIndex` 四个字段，`userPlayerList` 只能通过绑定流程修改。

缓存：不缓存。每次命令都读一次用户数据。

### 6.2 绑定 / 解绑流程

**绑定**（`绑定玩家 [服]`）：

1. 解析服务器；未指定则用 `mainServer`。
2. `bind_player_request(platform, user_id)` → `{"verifyCode": 五位数字}`
3. 回复：
   ```
   正在绑定来自 {服名} 账号，请将你的
   评论(个性签名)
   或者
   你的当前使用的卡组的卡组名(乐队编队名称)
   改为以下数字后，直接发送你的玩家id
   {验证码}
   ```
4. `matcher.got("player_id")` 等待下一条消息，超时 `tsugu_bind_timeout` 秒。
   - 超时 → `错误: 等待超时`
   - 非纯数字 → `错误: 无效的玩家id`（并重新等待）
5. `bind_player_verification(platform, user_id, server, player_id, "bind")`
6. 成功 → 回复文本 `绑定 {服名} 玩家 {player_id} 成功，正在生成玩家状态图片`，随后发玩家状态图（`search_player`）。

**解绑**（`解除绑定 [服]`）：同构，`bindingAction` 为 `"unbind"`。取当前该服务器上已绑定的 `playerId`，若不存在报 `用户在对应服务器上未绑定player`；验证通过后回复后端返回的文本。

验证码由后端内存缓存持有，有 TTL；过期后 `bind_player_verification` 会返回失败文本，直接透传。

### 6.3 玩家状态

```
玩家状态 [序号] [服]
```

- 给了序号：取 `userPlayerList[序号-1]`；越界报 `错误: 无效的绑定信息ID`。
- 没给序号：
  - 指定了服务器 → 取该服务器上的绑定；没有则报 `用户在对应服务器上未绑定player`。
  - 未指定服务器 → 若 `userPlayerList[userPlayerIndex].server == mainServer` 取该项，否则取列表中第一个属于 `mainServer` 的项。
- `userPlayerList` 为空 → `未绑定任何玩家`。
- 最终调 `search_player(player_id, server)` 出图。

### 6.4 玩家状态列表

纯文本：

```
已绑定玩家列表:
1. 国服: 10000000
2. 日服: 40474621
当前默认玩家绑定信息ID: 1
当前主服务器: 国服
默认显示服务器顺序: 国服, 日服
```

无绑定时第一段为 `未绑定任何玩家`，后续三行照常输出。

### 6.5 本地存储

用户数据不落本地库（见 6.1），但**群级设置需要**，因为 Tsugu 用户数据 API 以用户为键，表达不了「本群」这个维度。

用 `nonebot-plugin-orm` 建一张表：

```python
class GroupSetting(Model):
    __tablename__ = "tsugu_group_settings"
    group_openid: Mapped[str] = mapped_column(String(64), primary_key=True)
    gacha_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
```

读取语义：查不到该群的行时，视为默认值 `gacha_enabled=True`，**不预先插行**（只读命令不应该写库）。写入时才 upsert。

建表机制：`.env` 的 `ALEMBIC_STARTUP_CHECK=False` 让 `nonebot_plugin_orm` 在启动时跑 `migrate.sync revision`，从模型自动生成并应用迁移，无需手写迁移脚本。

**关于现有库**：`data/db.sqlite3` 里只有 `alembic_version` 和 `live_events`（旧 `live` 插件的 RSS 缓存，无保留价值），`data/nonebot_plugin_orm/migrations/live/` 是空的命名空间目录。因此直接删除这两者，让 ORM 用新模型从零重建，避免留着引用已删模型的陈旧迁移。

## 7. 发送层（`sender.py`）

### 7.1 结果转换

后端返回 `[{"type": "string"|"base64", "string": "..."}]`：

- `type == "string"` → `MessageSegment.text(s)`
- `type == "base64"` → `MessageSegment.image(b64decode(s))` → QQ 适配器识别为 `LocalAttachment`，自动走富媒体上传

### 7.2 QQ 被动消息条数上限

QQ 官方平台限制：**同一个 `msg_id` 最多回复 5 条被动消息**。因此不能把结果列表一对一地发出去。

切分与截断策略（`sender.py` 的 `send_result(matcher, items)`）：

1. 把连续的 `string` 段合并为一条文本消息。
2. 每个 `base64` 段单独作为一条图片消息。
3. 记合并后的消息条数为 `n`，上限为 `limit = tsugu_max_messages`。
4. 若 `n <= limit`：按顺序全部发出。
5. 若 `n > limit`：只发前 `limit - 1` 条，再补发一条 `结果过长，仅显示前 {limit - 1} 项`。

发送统一走 `matcher.send(...)` / `bot.send(event, ...)`，由适配器自动填 `msg_id` 与自增 `msg_seq`。

**不要**自己维护 `msg_seq`，也不要复用同一个 `matcher` 在多轮对话里跨事件发送——`_reply_seq` 是挂在事件对象上的，事件结束即失效。

### 7.3 可选的 @

`tsugu_at=true` 时，在第一条消息前插入 `MessageSegment.mention_user(event.get_user_id())`。QQ 官方 Bot 的 `get_user_id()` 返回 openid，可直接用于 mention。

引用回复由适配器根据事件自带的 `message_scene` 自动处理，不额外干预。

## 8. 错误处理

`tsugu-api-python` 在业务错误时抛 `FailedException`，其 `response["data"]` 是后端给的中文文案（以 `错误:` 开头），直接透传给用户。

按 HTTP 状态码映射的兜底文案（取自 Tsugu 前端）：

| 情况 | 文案 |
|---|---|
| HTTP 400 | `错误: 请求参数错误, 可能因为版本与后端服务器版本不一致` |
| HTTP 404 | `无法连接至后端服务器` |
| HTTP 422 | `错误: 无效的请求 (...)`（括号内为后端返回的 `data`） |
| HTTP 500 | `内部错误` |
| 网络异常 / 超时 | `错误: 后端服务器连接出错` |
| 用户数据接口失败 | 透传后端 `data` |

`tsugu_api_async.settings.max_retries` 设为 `tsugu_retries`。

## 9. 配置（`config.py`）

Pydantic 模型，字段全部 `TSUGU_` 前缀，与 `nonebot-plugin-tsugu-bangdream-bot` 同名同义：

| 字段 | 默认值 | 说明 |
|---|---|---|
| `tsugu_backend_url` | `http://tsugubot.com:8080` | 查询后端地址 |
| `tsugu_data_backend_url` | `http://tsugubot.com:8080` | 用户数据 / 车站后端地址 |
| `tsugu_platform` | `red` | 用户数据的平台命名空间 |
| `tsugu_use_easy_bg` | `False` | 简易背景，快但简陋 |
| `tsugu_compress` | `True` | 后端压缩图片（对齐 mainline Tsugu） |
| `tsugu_no_space` | `False` | 允许命令头后不跟空格 |
| `tsugu_at` | `False` | 结果前 `@` 用户 |
| `tsugu_timeout` | `30` | 后端请求超时（秒） |
| `tsugu_retries` | `3` | 重试次数 |
| `tsugu_proxy` | `""` | 代理地址 |
| `tsugu_backend_proxy` | `False` | 查询后端是否走代理 |
| `tsugu_data_backend_proxy` | `False` | 用户数据后端是否走代理 |
| `tsugu_max_messages` | `5` | 单次回复的被动消息条数上限 |
| `tsugu_bind_timeout` | `300` | 绑定流程等待秒数 |
| `tsugu_bandori_station_token` | `None` | `None` 时用 Tsugu 公共令牌 |

另加一组别名配置项，与 nonebot-tsugu 同名：`tsugu_search_card_aliases`、`tsugu_card_illustration_aliases`、`tsugu_search_character_aliases`、`tsugu_search_event_aliases`、`tsugu_search_song_aliases`、`tsugu_song_chart_aliases`、`tsugu_song_random_aliases`、`tsugu_song_meta_aliases`、`tsugu_event_stage_aliases`、`tsugu_search_gacha_aliases`、`tsugu_search_player_aliases`、`tsugu_ycm_aliases`、`tsugu_ycx_aliases`、`tsugu_ycx_all_aliases`、`tsugu_lsycx_aliases`、`tsugu_gacha_simulate_aliases`、`tsugu_bind_player_aliases`、`tsugu_unbind_player_aliases`、`tsugu_main_server_aliases`、`tsugu_default_servers_aliases`、`tsugu_player_status_aliases`、`tsugu_player_list_aliases`、`tsugu_switch_index_aliases`、`tsugu_open_forward_aliases`、`tsugu_close_forward_aliases`。类型均为 `set[str]`，默认空集。

插件启动时把配置写入 `tsugu_api_async.settings`（`backend_url`、`userdata_backend_url`、`timeout`、`max_retries`、`proxy`、`backend_proxy`、`userdata_backend_proxy`、`use_easy_bg`、`compress`）。

## 10. 文件结构

```
src/plugins/tsugu/
├── __init__.py          插件入口：注册全部 matcher；启动时写入 tsugu_api settings
├── config.py            Pydantic Config
├── constants.py         服务器表、档位表、车牌关键词、错误文案
├── rule.py              命令头 trie、shortcut 正则、车牌正则、参数工具
├── api.py               tsugu-api-python 封装 + FailedException → 文案
├── sender.py            [{"type","string"}] → Message，条数上限与拆分
├── user.py              用户数据读写、绑定/解绑流程、玩家状态
├── car.py               车牌自动转发消息监听器
├── db.py                ORM 模型（GroupSetting）与读写函数
└── commands/
    ├── __init__.py      汇总注册，导出命令元数据供 help 使用
    ├── card.py          查卡、查卡面
    ├── character.py     查角色
    ├── event.py         查活动、查试炼
    ├── song.py          查曲、查谱面、随机曲、查询分数表
    ├── gacha.py         查卡池、抽卡模拟、抽卡开关
    ├── cutoff.py        ycx、ycxall、lsycx
    ├── player.py        查玩家
    ├── station.py       ycm
    ├── settings.py      绑定/解绑/主服务器/显示服务器/玩家状态/玩家默认ID/车牌转发
    └── help.py          帮助命令与帮助文本
```

## 11. 依赖变更

`pyproject.toml` 的 `dependencies`：

```toml
dependencies = [
    "nonebot2[fastapi]>=2.5.0",
    "nonebot2[httpx]>=2.5.0",
    "nonebot2[websockets]>=2.5.0",
    "nonebot-adapter-qq>=1.7.0",
    "nonebot-plugin-orm[sqlite]>=0.8.0",
    "tsugu-api-python[httpx]>=1.5.10",
]
```

**移除仅 `nonebot-plugin-apscheduler`**（旧 `live` 插件的定时爬取）。**保留 `nonebot2[websockets]`** —— QQ 适配器连接 QQ 网关依赖它提供的 `WebSocketClientMixin` 驱动。**保留 `nonebot-plugin-orm[sqlite]`** —— 群级设置需要（见 6.5），同时带出 `nonebot-plugin-localstore`。

移除 `beautifulsoup4`（旧 `live` 插件的 RSS 解析）等随之不再需要的传递依赖，同步重生成 `requirements.txt`。

`.env` 只需改一行 —— `DRIVER` 补上 websockets：

```
ENVIRONMENT=dev
DRIVER=~fastapi+~httpx+~websockets
LOCALSTORE_USE_CWD=true
SQLALCHEMY_DATABASE_URL=sqlite+aiosqlite:///data/db.sqlite3
ALEMBIC_STARTUP_CHECK=False
```

`LOCALSTORE_USE_CWD`、`SQLALCHEMY_DATABASE_URL`、`ALEMBIC_STARTUP_CHECK` 三个都**保留**：前者把 migrations 与数据目录固定在项目内，后两者是 ORM 建表所必需。

## 12. 验证方式

不写自动化测试。靠以下手段验证：

1. `ruff check src/` 与 `ruff format --check src/` 通过。
2. `pyright src/` 通过。
3. `nb run --reload` 能正常启动，插件加载无报错。
4. 启动后 `data/db.sqlite3` 出现 `tsugu_group_settings` 表，且不含残留的 `live_events`。
5. 用 `python -c` 直接调用 `api.py` 的各封装函数，对公共后端发真实请求，确认返回结构被正确解析。
6. 用构造的假 QQ 事件对象走一遍 `rule.py` 的分派逻辑，确认 `@bot 查卡 1399`、`查卡947`（开关开/关两种）、`日服模式`、`国服玩家状态`、`123456 大分车` 各自的匹配结果符合预期。这是本项目最容易出错的一环，值得单独验。
7. 真机联调：把 Bot 连上 QQ 官方沙箱，逐条验证 5.1、5.2、5.3 的命令。

## 13. 已知限制

1. **群聊中的车牌自动转发收不到消息**。QQ 官方 Bot 群里只推送 `@` 了它的消息，除非申请全量消息权限。逻辑已完整实现，私聊可用，群聊待权限到位后自动生效。
2. **单次回复最多 5 条被动消息**。查询结果超出部分会被截断并提示。
3. **依赖第三方公共服务**。`tsugubot.com:8080` 的可用性、限流、数据准确性不由本项目控制。后端地址可配置，便于日后切到自建实例。
4. **`platform="red"` 与官方 Tsugu QQ Bot 共用用户数据命名空间**。这是刻意的设计（一次绑定多处使用），但意味着两边的绑定与设置会互相可见、互相影响。
5. `tsugu-api-python` 与 Tsugu 后端均非本项目维护，接口若变更需要跟进。
6. **群级抽卡开关不做权限校验**，任何群成员都能开关。QQ 官方 Bot 的群消息事件不提供成员角色字段，做不到 mainline 那种「仅管理员」判断。详见 5.3。
