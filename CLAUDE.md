# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

kasumi_bot is a QQ chatbot frontend for **Tsugu BanGDream Bot**, built with [NoneBot2](https://nonebot.dev/) on the official QQ adapter (`nonebot-adapter-qq`). Python 3.9+, developed against 3.13.

The bot owns no game data and renders nothing itself. Every query is answered by the **public Tsugu backend** at `http://tsugubot.com:8080` (overridable via config); the plugin's job is trigger matching, argument parsing, and translating the backend's unified response into QQ messages. User data lives in that same backend, shared with the official Tsugu QQ bot.

## Common Commands

```bash
# Run the bot locally with hot-reload
nb run --reload

# Install dependencies
pip install -r requirements.txt

# Lint and format
ruff check src/
ruff format src/

# Type-check
pyright src/

# Docker build and run
docker-compose up --build
```

## Architecture

**Framework flow:**

```
QQ official Bot <--WebSocket--> nonebot-adapter-qq --> NoneBot2
    --> src/plugins/tsugu/ --> httpx --> Tsugu backend (tsugubot.com:8080)
```

FastAPI is the ASGI server; httpx handles outbound HTTP, wrapped by `tsugu-api-python` (imported as `tsugu_api_async`).

**Plugin system:** Plugins live under `src/plugins/`, each as a Python package. Plugin directories are configured in `pyproject.toml` under `[tool.nonebot]`. `tsugu` is the only plugin that does real work; `nonebot_plugin_orm` and `nonebot_plugin_localstore` are loaded as dependencies.

### Why the plugin does not use `on_command`

In QQ groups the bot only receives messages that **@-mention it**, and the adapter parses that mention into a `MentionUser` segment at `message[0]`. NoneBot's `TrieRule.get_value` only inspects `message[0]` and gives up entirely when it is not a text segment — so standard `on_command` / `on_startswith` matchers never fire in groups.

The plugin therefore registers exactly one `on_message` with `priority=10, block=True` and dispatches itself. All trigger logic lives in `rule.py` as pure functions (`normalize`, `match_car`, `apply_shortcut`, `match_command`, `build_head_table`), which keeps it importable and testable without a running NoneBot.

### Plugin layout — `src/plugins/tsugu/`

| File | Responsibility |
| --- | --- |
| `__init__.py` | Registers the single `on_message` dispatcher and reproduces the decision order: pending bind flow → car-plate forwarding → command match. Merges `.env` aliases into the command-head table. Owns `config` / `tsugu_api_async.settings` wiring. |
| `rule.py` | Pure trigger layer. Command-head trie, car-plate regex, two shortcut patterns (`X服模式`, `X服玩家状态`), shortcut expansion, and `normalize`. No NoneBot runtime dependency. |
| `commands/` | One module per command family (`card`, `character`, `cutoff`, `event`, `gacha`, `help`, `player`, `settings`, `song`, `station`). Each handler self-registers via `@register("<command_id>")` into `HANDLERS`; `__init__.py` also defines `Ctx`, the per-invocation context passed to every handler. |
| `sender.py` | Translates the backend's `[{type: 'string'|'base64'}]` response into QQ messages: merges consecutive text, splits images into separate messages, truncates at the per-message limit, and prepends the optional @-mention to the **first** message only. |
| `api.py` | Wraps `tsugu_api_async`. Normalizes backend exceptions into the same response shape as success, so callers handle one type. |
| `user.py` | User-data view model (`User`), player-binding selection rules, and the in-memory `pending` state for the interactive bind flow. |
| `db.py` | The only local table, `tsugu_group_settings` — per-group settings keyed by `group_openid`. |
| `car.py` | Car-plate auto-forwarding (5/6 leading digits). In private chats only; see "Known limitations". |
| `config.py` | Pydantic `Config` model. Field names deliberately mirror `nonebot-plugin-tsugu-bangdream-bot`. |
| `constants.py` | Static tables and copy: server IDs/names, tier lists, command heads, alias fields map, keyword lists, error strings. |

**Command count:** 30 registered command IDs (29 commands plus `bind_reply`). `bind_reply` is the pending-bind-flow reply handler and is intentionally absent from `COMMAND_HEADS`, so it never appears in `help`. Note that `grep -c '@register' src/plugins/tsugu/commands/*.py` reports 31 because `commands/__init__.py` mentions `@register` inside its docstring; the real total is 30.

### Local persistence

Nothing important is stored locally. The one table that exists goes through `nonebot_plugin_orm`, using `SQLALCHEMY_DATABASE_URL` (SQLite by default). Schema is applied at startup by alembic; the resulting database has exactly two tables: `alembic_version` and `tsugu_group_settings`.

## Deployment Constraints

These two are easy to break because nothing in the code enforces them.

### gunicorn must run a single worker

The bind flow's pending state (`user.pending` in `user.py`) is **plain process memory**. With more than one worker, a user's next message can be routed to a different process, where no pending bind exists — the handler then treats it as an ordinary message, and the bind **silently breaks intermittently**. Symptoms look like random unconsumed replies, not errors.

Today this is safe only by accident: `Dockerfile` sets `ENV MAX_WORKERS 1`, while `docker/gunicorn_conf.py` would otherwise default to `min(max(workers_per_core * cores, 2), MAX_WORKERS)` — i.e. several workers on any multi-core host. **The dependency is implicit.** Anyone running gunicorn directly, or overriding `MAX_WORKERS` / `WORKERS_PER_CORE` / `WEB_CONCURRENCY`, will multi-process the bot and reintroduce the bug. If you ever need real multi-worker scaling, move `user.pending` into the database first.

### `.env` values for set-typed settings must be JSON arrays

All `tsugu_*_aliases` fields are `set[str]`. In `.env` they must be written as JSON arrays:

```dotenv
TSUGU_SEARCH_CARD_ALIASES=["查卡","查卡牌"]
```

A comma-separated value (`TSUGU_SEARCH_CARD_ALIASES=查卡,查卡牌`) raises `nonebot.config.SettingsError: error parsing env var "tsugu_search_card_aliases"` at startup. NoneBot's own `DotEnvSettingsSource` treats any complex field as JSON and, for a plain `set[str]`, calls `json.loads` with `allow_parse_failure=False`. This matches `nonebot-plugin-tsugu-bangdream-bot` (which also declares these as `Set[str]`) — it is parity with upstream, not a defect in this repo.

## Known Limitations

- **Group car plates are not received.** The bot only sees @-mentions, so an unmentioned `123456 大分e` never arrives in a group. Private chats work. `car.py` is complete and will start working if full-message permissions are ever granted.
- **5 messages per reply.** QQ's official platform caps passive replies at 5 per `msg_id`; `sender.py` truncates beyond that with a notice.
- **Depends on the public Tsugu backend.** No offline mode; upstream downtime is this bot's downtime.
- **Shares the `red` user-data namespace** with the official Tsugu QQ bot (`TSUGU_PLATFORM`, default `"red"`). Bindings are visible to both, by design.
- **The group-level gacha switch has no permission check.** Any member can toggle it via `开启抽卡` / `抽卡 off`; it is stored per-group but not restricted.

## Code Style

- Linter/formatter: **Ruff** (line length 88, target Python 3.9, LF endings)
- Type checker: **Pyright** (standard mode, Python 3.9 target)
- Ruff rule sets: pyflakes, pycodestyle, isort, mccabe, pep8-naming, pylint, pyupgrade, bugbear, comprehensions, type-annotations, FastAPI

## Adding a New Command

1. Add the command ID and its heads to `COMMAND_HEADS` in `src/plugins/tsugu/constants.py` (longer heads first — matching is longest-prefix). If the command is user-facing, it will show up in `help` automatically.
2. Write the handler in the appropriate `src/plugins/tsugu/commands/<family>.py` and decorate it with `@register("<command_id>")`. The decorator registers into `HANDLERS`, keyed by the same ID.
3. Read `arg` from the `Ctx` passed in and reply with `ctx.reply(items)` (backend response) or `ctx.reply_text(...)`. Use `ctx.local_only()` for anything that only makes sense in a private chat.
4. If the command needs a configurable alias, add a `tsugu_<name>_aliases: set[str]` field to `Config` and map it in `ALIAS_FIELDS`.

The dispatcher in `__init__.py` needs no changes — it looks the handler up in `HANDLERS` and logs a warning if an ID has no handler.

## Environment Files

- `.env` — base config. Current keys: `ENVIRONMENT`, `DRIVER`, `LOCALSTORE_USE_CWD`, `SQLALCHEMY_DATABASE_URL`, `ALEMBIC_STARTUP_CHECK`. Add plugin settings here in `TSUGU_*` form.
- `.env.dev` — local dev overrides (`LOG_LEVEL=DEBUG`)
- `.env.prod` — production secrets (injected at deploy time). Requires `QQ_BOT_ID`, `QQ_BOT_TOKEN`, `QQ_BOT_SECRET`.

**`DRIVER` must include `~websockets`:**

```dotenv
DRIVER=~fastapi+~httpx+~websockets
```

The QQ adapter connects to the platform over a WebSocket, and refuses to set up on a driver without `WebSocketClientMixin`:

```
RuntimeError: Current driver ~fastapi+~httpx does not support websocket client!
QQ Adapter need a WebSocketClient Driver to work.
```

Note when this bites: the adapter only enforces it when `QQ_BOTS` is non-empty (`any(bot.use_websocket for bot in qq_config.qq_bots)`). With no `QQ_BOT_ID` configured — as in a bare local checkout — the check is skipped and the bot boots fine **without** `~websockets`. The failure therefore surfaces only once you deploy with credentials, which is the worst time to discover it. Keep `~websockets` in `DRIVER` everywhere.

## Design Docs

The design spec and implementation plan for the Tsugu port live in:

- `docs/superpowers/specs/` — the design spec (architecture, command list, deployment notes)
- `docs/superpowers/plans/` — the step-by-step implementation plan

Consult them before making structural changes.
