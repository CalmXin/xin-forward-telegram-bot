from datetime import datetime, timezone
from pathlib import Path

import yaml
from loguru import logger

from src.config import BASE_DIR


# ========== 工具类 ==========

class YamlUtil:
    def __init__(self, yaml_file_path: str | Path):
        self.yaml_file_path = Path(yaml_file_path)
        self._yaml_data = yaml.safe_load(self.yaml_file_path.read_text(encoding='utf-8'))

    def get(self, *args) -> any:
        value = self._yaml_data
        try:
            for key in args:
                value = value[key]
        except KeyError:
            return None
        return value


# ========== 工具函数 ==========

def get_channel_url_by_id(channel_id: int, message_id: int) -> str:
    """生成频道的消息连接"""
    if not str(channel_id).startswith('-100'):
        raise ValueError("频道 ID 格式错误")
    return f"https://t.me/c/{str(channel_id)[4:]}/{message_id}"


def get_channel_url_by_username(channel_username: str, message_id: int) -> str:
    return f"https://t.me/{channel_username}/{message_id}"


def setup_logger():
    logger.add(
        f"{BASE_DIR}/logs/app_{datetime.now().strftime('%Y_%m_%d')}.log",
        rotation="10 MB",  # 每个文件最大10MB
        retention="30 days",
        compression="zip"  # 压缩旧日志为 zip
    )
    return logger


def utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)
