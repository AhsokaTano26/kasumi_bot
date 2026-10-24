# kuma_health Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan in the current session.

**Goal:** 每 60 秒检查真实状态并向已有 Kuma Push 监控发送 up/down。

**Architecture:** NoneBot 生命周期管理后台任务；独立健康检查模块复用 QQ 适配器，探测本机 Webhook 后主动调用身份接口。

**Tech Stack:** Python 3.10+、NoneBot2、QQ Adapter、HTTPX、unittest。

**Spec:** `docs/superpowers/specs/2026-10-24-kuma-health-design.md`

## Global Constraints

- 直接在 `main` 工作，不创建分支或 worktree；按用户后续指令提交并推送。
- 唯一新增配置为 `KUMA_PUSH_URL`；不增加依赖。
- 周期 60 秒、请求超时 10 秒；不得把配置 URL 中的旧 up 当作实际状态。

## Review Focus

- Webhook 未收到事件时仍能主动查询 QQ 身份。
- QQ 失败、空身份、无账号、Webhook 失败均发送 down。
- Kuma URL 旧查询参数被正确替换，失败不终止下一次上报。
- 未配置时不启动任务；退出时取消任务；等待 60 秒后开始检查。
- 多账号任意一个失败不能发送 up。

### Task 1: 插件、测试和使用说明

**Files:** 新建 `src/plugins/kuma_health/{__init__,config,health}.py`、
`tests/test_kuma_health.py`；更新 `README.md`。

**Interfaces:** `HealthReporter(driver, push_url)` 提供
`async report_once(client) -> None`、`async run() -> None`；插件入口注册启动和退出钩子。

- [x] 先写状态判断、参数覆盖、重试与生命周期行为测试，运行并确认新插件缺失导致失败。
- [x] 实现插件配置、检查和上报循环，使测试通过。
- [x] 补充 README 配置和监控说明。
- [x] 运行完整 unittest、Ruff 和 Pyright；检查 diff 并进行代码审查。

### Task 2: 更新项目插件和依赖（用户追加要求）

**Files:** `pyproject.toml`、`requirements.txt`、`README.md`。

- [x] 从 PyPI 解析所有依赖最新兼容稳定版本，保留 Python 3.10+ 与跨平台支持。
- [x] 声明直接使用的 HTTPX 和原依赖清单已有的 nb-cli、Docker 插件开发工具。
- [x] 在独立环境安装更新后的完整依赖清单。
- [x] 使用更新后的环境运行完整测试、格式检查、类型检查以及应用生命周期启动验证。

## 验证结果

- 更新后的 Python 3.13 环境：`python -m unittest discover -s tests -v`，20 项通过。
- Ruff 0.17.2 检查与格式检查通过；Pyright 1.1.414 检查为 0 errors。
- `uv pip check` 检查安装的 84 个包，没有依赖冲突。
- 独立临时数据库启动验证通过：环境变量读取、两个插件加载、实际生命周期启动、
  Webhook 验证、ORM 自动迁移和任务退出清理。
- 独立审查发现的 HTTPX INFO 日志泄露 Push 令牌问题已经回归测试复现并修复；
  仅屏蔽当前 Kuma 上报上下文的 HTTPX 日志，保留其他请求日志。
- 多账号失败时等待其他身份检查结束或超时，防止遗留探测任务；已测试复现并修复。
- 按用户后续指令，在确认远端状态与验证通过后提交并推送 `main`。
  验证未连接实际生产 QQ 或 Kuma 端点。
