from pathlib import Path

from telebot import TeleBot

from src.config import BASE_DIR
from src.core import DatabaseClient
from src.entities import BaseEntity
from src.services import BotService, Repository
from src.utils import YamlUtil, setup_logger

logger = setup_logger()


class Application:
    """运行类"""

    def __init__(self):
        self.config = YamlUtil(BASE_DIR / 'config.yaml')
        self.bot = TeleBot(self.config.get('bot', 'token'))

        self.db: DatabaseClient | None = None
        self._setup()
        self.session = self.db.get_session()
        self.repo = Repository(self.session)
        self.service = BotService(self.bot, self.repo)

        logger.info('初始化成功')

    def __del__(self):
        self.session.close()  # 关闭数据库会话

    def _setup(self) -> None:
        """初始化"""
        db_file_path = BASE_DIR / 'db' / 'data.db'
        db_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = DatabaseClient(f'sqlite:///{db_file_path}')
        BaseEntity.metadata.create_all(self.db.engine)

    def execute(self) -> None:
        """执行"""
        # 获取最新的记录
        messages_dict: dict[str, list[int]] = self.service.check_channel_messages()
        logger.info(messages_dict)
        # 将某个频道的消息发送到群组对应的话题
        forward_mapping: dict = self.config.get('forward_mapping')
        group_chat_id = self.config.get('group_chat_id')
        for channel_id, urls in messages_dict.items():
            # 跳过没有映射的频道
            if channel_id not in forward_mapping.keys():
                continue
            # 开始转发
            channel_title = self.service.get_channel_title(int(channel_id))
            for url in urls:
                self.service.send_message_to_group(
                    html_text=f'#{channel_title} <a href="{url}">{url}</a>',
                    group_chat_id=group_chat_id,
                    message_thread_id=forward_mapping[channel_id]
                )
