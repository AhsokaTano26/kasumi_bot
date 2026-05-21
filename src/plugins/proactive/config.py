from pydantic import BaseModel


class Config(BaseModel):
    """主动消息测试插件配置"""

    proactive_group_id: str = ""
