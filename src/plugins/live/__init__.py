from datetime import date, datetime, timezone

import nonebot
from nonebot import get_plugin_config, on_command, require
from nonebot.adapters.qq import Message
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from sqlalchemy import select

from .config import Config

require("nonebot_plugin_apscheduler")
require("nonebot_plugin_orm")

from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_orm import async_scoped_session

from .crawler import crawl_and_store
from .db import LiveEvent

__plugin_meta__ = PluginMetadata(
    name="live",
    description="BanG Dream 演出信息查询",
    usage="发送 /未来演出 或 /live 查询近期演出",
    config=Config,
)

config = get_plugin_config(Config)
MAX_RESULTS = 5


# 启动时爬取
@nonebot.get_driver().on_startup
async def _startup() -> None:
    try:
        await crawl_and_store()
    except Exception:  # noqa: BLE001
        nonebot.logger.exception("启动时爬取演出信息失败")


# 定时任务：每天 00:00 爬取
@scheduler.scheduled_job("cron", hour=0, minute=0, id="crawl_live_events")
async def _scheduled_crawl() -> None:
    try:
        await crawl_and_store()
    except Exception:  # noqa: BLE001
        nonebot.logger.exception("定时爬取演出信息失败")


# 命令：/未来演出 或 /live
live_cmd = on_command("live", aliases={"未来演出"}, priority=10, block=True)


@live_cmd.handle()
async def handle_live(
    session: async_scoped_session, args: Message[str] = CommandArg()
) -> None:
    band_filter = args.extract_plain_text().strip() or None
    today = datetime.now(tz=timezone.utc).date()

    result = await session.execute(select(LiveEvent))
    all_events = result.scalars().all()

    # 筛选未来演出，记录最近日期用于排序
    upcoming: list[tuple[date, LiveEvent]] = []
    for event in all_events:
        normalized = [
            datetime.strptime(d, "%Y.%m.%d").replace(tzinfo=timezone.utc).date()
            for d in event.date_list
            if d
        ]
        future_dates = sorted(d for d in normalized if d >= today)
        if not future_dates:
            continue
        if band_filter and band_filter.lower() not in event.bands.lower():
            continue
        upcoming.append((future_dates[0], event))

    # 按最近日期排序，取前 5 条
    upcoming.sort(key=lambda x: x[0])
    results = [ev for _, ev in upcoming[:MAX_RESULTS]]

    if not results:
        if band_filter:
            await live_cmd.finish(f"没有找到 {band_filter} 的近期演出信息")
        await live_cmd.finish("暂无近期演出信息")

    lines = ["近期演出信息：\n"]
    for i, ev in enumerate(results, 1):
        ev_dict = ev.to_dict()
        lines.append(f"{i}. {ev_dict['title']}")
        lines.append(f"   时间：{ev_dict['dates']}")
        if ev_dict["venue"]:
            lines.append(f"   地点：{ev_dict['venue']}")
        if ev_dict["bands"]:
            lines.append(f"   乐队：{ev_dict['bands']}")
        lines.append(f"   链接：{ev_dict['link']}")
        lines.append("")

    await live_cmd.finish("\n".join(lines))


# 命令：/刷新演出 手动触发爬取
refresh_cmd = on_command("refreshlive", aliases={"刷新演出"}, priority=10, block=True)


@refresh_cmd.handle()
async def handle_refresh() -> None:
    try:
        count = await crawl_and_store()
        await refresh_cmd.send(f"演出信息刷新完成，共处理 {count} 条")
    except Exception:  # noqa: BLE001
        await refresh_cmd.finish("刷新失败，请查看日志")
