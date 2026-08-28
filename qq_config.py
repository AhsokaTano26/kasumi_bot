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


class InvalidQQBotsError(RuntimeError):
    """QQ_BOTS is not a JSON array of bot objects."""


class IncompleteQQBotConfigError(RuntimeError):
    """One or more required flat QQ bot variables are missing."""

    def __init__(self, missing: list[str]) -> None:
        super().__init__(f"Missing required QQ bot variables: {', '.join(missing)}")


class InvalidQQBotIntentError(TypeError):
    """A QQ bot's intent setting is not an object."""


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
    """
    env = environment if environment is not None else os.environ
    configured_bots = env.get("QQ_BOTS")

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
        bot.setdefault("use_websocket", True)
        intent = bot.setdefault("intent", {})
        if not isinstance(intent, dict):
            raise InvalidQQBotIntentError
        intent.setdefault("c2c_group_at_messages", True)

    env["QQ_BOTS"] = json.dumps(bots, separators=(",", ":"))
