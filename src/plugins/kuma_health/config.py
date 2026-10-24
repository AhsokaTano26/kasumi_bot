"""Uptime Kuma Push 配置。"""

from pydantic import BaseModel, Field


class Config(BaseModel):
    """留空时不启动健康上报。"""

    kuma_push_url: str = Field(default="", repr=False)
