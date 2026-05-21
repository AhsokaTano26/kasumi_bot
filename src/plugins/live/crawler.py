import json
import xml.etree.ElementTree as ET

import httpx
from bs4 import BeautifulSoup
from nonebot import logger
from nonebot_plugin_orm import get_session

from .db import LiveEvent

RSS_URL = "https://bangdream.tano.asia/rss.xml"
MAX_SUMMARY_LENGTH = 200


async def fetch_rss() -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(RSS_URL)
        resp.raise_for_status()
        return resp.text


def _extract_field(soup: BeautifulSoup, label: str) -> str:
    """从 description HTML 中提取指定字段的值"""
    for strong in soup.find_all("strong"):
        if strong.string and label in strong.string:
            parts: list[str] = []
            for sibling in strong.next_siblings:
                if sibling.name in {"strong", "br"}:
                    break
                if isinstance(sibling, str):
                    parts.append(sibling.strip())
                elif sibling.name == "a":
                    parts.append(sibling.get_text(strip=True))
            return " ".join(parts).strip()
    return ""


def _parse_dates(date_str: str) -> list[str]:
    """解析日期字符串：'2026.09.22 / 2026.09.23' -> ['2026.09.22', '2026.09.23']"""
    if not date_str:
        return []
    parts = [d.strip() for d in date_str.replace("/", " / ").split(" / ")]
    return [p for p in parts if p]


def parse_rss(xml_text: str) -> list[dict[str, str | list[str]]]:
    root = ET.fromstring(xml_text)
    items: list[dict[str, str | list[str]]] = []

    for item in root.findall(".//item"):
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        desc_html = item.findtext("description", "")

        soup = BeautifulSoup(desc_html, "html.parser")

        date_str = _extract_field(soup, "演出时间")
        summary = _extract_field(soup, "简介")
        venue = _extract_field(soup, "演出地点")
        bands = _extract_field(soup, "演出乐队")

        if len(summary) > MAX_SUMMARY_LENGTH:
            summary = summary[:MAX_SUMMARY_LENGTH] + "..."

        items.append(
            {
                "link": link,
                "title": title,
                "dates": _parse_dates(date_str),
                "venue": venue,
                "bands": bands,
                "summary": summary,
            }
        )

    return items


async def crawl_and_store() -> int:
    """爬取 RSS 并存入数据库，返回处理条数"""
    xml_text = await fetch_rss()
    events = parse_rss(xml_text)

    count = 0
    session = get_session()
    async with session.begin():
        for event in events:
            dates = event["dates"]
            if not dates:
                continue

            link = str(event["link"])
            existing = await session.get(LiveEvent, link)
            if existing:
                existing.title = str(event["title"])
                existing.dates = json.dumps(dates)
                existing.venue = str(event.get("venue", ""))
                existing.bands = str(event.get("bands", ""))
                existing.summary = str(event.get("summary", ""))
            else:
                session.add(
                    LiveEvent(
                        link=link,
                        title=str(event["title"]),
                        dates=json.dumps(dates),
                        venue=str(event.get("venue", "")),
                        bands=str(event.get("bands", "")),
                        summary=str(event.get("summary", "")),
                    )
                )
            count += 1

    logger.info(f"演出信息爬取完成，共处理 {count} 条")
    return count
