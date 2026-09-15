"""Prepare QQ adapter settings from flat environment variables."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import MutableMapping


_FLAT_QQ_FIELDS = {
    "id": "QQ_BOT_ID",
    "token": "QQ_BOT_TOKEN",
    "secret": "QQ_BOT_SECRET",
}

_USE_WEBSOCKET_VARIABLE = "QQ_USE_WEBSOCKET"

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})


class InvalidQQBotsError(RuntimeError):
    """QQ_BOTS is not a JSON array of bot objects."""


class IncompleteQQBotConfigError(RuntimeError):
    """One or more required flat QQ bot variables are missing."""

    def __init__(self, missing: list[str]) -> None:
        super().__init__(f"Missing required QQ bot variables: {', '.join(missing)}")


class InvalidQQBotIntentError(TypeError):
    """A QQ bot's intent setting is not an object."""


class InvalidQQUseWebsocketError(ValueError):
    """``QQ_USE_WEBSOCKET`` is not a recognisable boolean."""

    def __init__(self, value: str) -> None:
        accepted = ", ".join(sorted(_TRUE_VALUES | _FALSE_VALUES))
        super().__init__(
            f"{_USE_WEBSOCKET_VARIABLE} must be one of {accepted}; got {value!r}"
        )


def _use_websocket_default(env: MutableMapping[str, str]) -> bool:
    """Read the flat WebSocket switch.

    Absent or empty means the adapter's own default (``True``).  An
    unrecognised value raises instead of silently falling back, because
    someone who wrote the variable meant it to take effect.
    """
    raw = env.get(_USE_WEBSOCKET_VARIABLE)
    if raw is None or not raw.strip():
        return True

    value = raw.strip().lower()
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    raise InvalidQQUseWebsocketError(raw)


def _load_bots(value: str) -> list[dict[str, Any]]:
    """Decode QQ_BOTS and reject invalid settings before NoneBot starts."""
    try:
        bots = json.loads(value)
    except json.JSONDecodeError as error:
        raise InvalidQQBotsError from error

    if not isinstance(bots, list) or not all(isinstance(bot, dict) for bot in bots):
        raise InvalidQQBotsError
    return bots


def configure_qq_bots(environment: MutableMapping[str, str] | None = None) -> None:
    """Build ``QQ_BOTS`` from flat variables and apply project defaults.

    A single QQ bot can be configured without JSON using ``QQ_BOT_ID``,
    ``QQ_BOT_TOKEN`` and ``QQ_BOT_SECRET``.  A pre-existing ``QQ_BOTS`` value
    remains supported for multi-bot deployments.

    ``QQ_USE_WEBSOCKET`` sets the default ``use_websocket`` for every bot that
    does not specify its own, so a webhook deployment can turn the adapter's
    WebSocket connection off without switching to JSON.  Bots configured
    through ``QQ_BOTS`` keep whatever they set themselves.
    """
    env = environment if environment is not None else os.environ
    use_websocket_default = _use_websocket_default(env)
    configured_bots = env.get("QQ_BOTS")

    # 显式标注是必需的：下面扁平分支推导出的是 dict[str, str | None]，
    # 两个分支合并后 pyright 会按它收紧 values 类型，导致后面
    # setdefault("use_websocket", bool) / setdefault("intent", dict) 全部爆类型。
    bots: list[dict[str, Any]]

    if configured_bots:
        bots = _load_bots(configured_bots)
    else:
        bot = {field: env.get(variable) for field, variable in _FLAT_QQ_FIELDS.items()}
        supplied = [
            variable for variable in _FLAT_QQ_FIELDS.values() if env.get(variable)
        ]
        if not supplied:
            return

        missing = [
            variable for field, variable in _FLAT_QQ_FIELDS.items() if not bot[field]
        ]
        if missing:
            raise IncompleteQQBotConfigError(missing)
        bots = [bot]

    for bot in bots:
        bot.setdefault("use_websocket", use_websocket_default)
        intent = bot.setdefault("intent", {})
        if not isinstance(intent, dict):
            raise InvalidQQBotIntentError
        intent.setdefault("c2c_group_at_messages", True)

    env["QQ_BOTS"] = json.dumps(bots, separators=(",", ":"))
