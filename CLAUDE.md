# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

kasumi_bot is a QQ chatbot built with [NoneBot2](https://nonebot.dev/) using the official QQ adapter (`nonebot-adapter-qq`). Python 3.9+, developed against 3.13.

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

**Framework flow:** QQ Platform <-> nonebot-adapter-qq <-> NoneBot2 Core <-> Plugin Handlers, with FastAPI as the ASGI server and httpx for outbound HTTP.

**Plugin system:** Plugins live under `src/plugins/`, each as a Python package with `__init__.py` (registers command handlers via `on_command()`) and `config.py` (Pydantic config model). Plugin directories are configured in `pyproject.toml` under `[tool.nonebot]`.

**Entry points:**
- Local dev: `nb run` reads `pyproject.toml` and `.env`/`.env.dev`, auto-discovers plugins, starts FastAPI with hot-reload
- Production: Gunicorn -> Uvicorn workers -> `docker/_main.py` -> `nonebot.get_asgi()`, listening on port 8080

**Existing plugins:** `basic` (ping, hello, help), `entertainment` (random, joke, dice), `test` (empty scaffold)

## Code Style

- Linter/formatter: **Ruff** (line length 88, target Python 3.9, LF endings)
- Type checker: **Pyright** (standard mode, Python 3.9 target)
- Ruff rule sets: pyflakes, pycodestyle, isort, mccabe, pep8-naming, pylint, pyupgrade, bugbear, comprehensions, type-annotations, FastAPI

## Adding a New Plugin

Create a new directory under `src/plugins/` with `__init__.py` and `config.py`. Register command handlers in `__init__.py` using NoneBot2's `on_command()` API. The plugin will be auto-discovered on next startup.

## Environment Files

- `.env` — base config (LOG_LEVEL)
- `.env.dev` — local dev overrides (ENVIRONMENT=dev, DRIVER=~fastapi+~httpx)
- `.env.prod` — production secrets (injected at deploy time)
