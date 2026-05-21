import json

from nonebot_plugin_orm import Model
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column


class LiveEvent(Model):
    __tablename__ = "live_events"

    link: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    dates: Mapped[str] = mapped_column(Text)  # JSON 数组
    venue: Mapped[str] = mapped_column(String, default="")
    bands: Mapped[str] = mapped_column(String, default="")
    summary: Mapped[str] = mapped_column(Text, default="")

    @property
    def date_list(self) -> list[str]:
        return json.loads(self.dates)

    def to_dict(self) -> dict[str, str]:
        return {
            "title": self.title,
            "dates": " / ".join(self.date_list),
            "venue": self.venue,
            "bands": self.bands,
            "summary": self.summary,
            "link": self.link,
        }
