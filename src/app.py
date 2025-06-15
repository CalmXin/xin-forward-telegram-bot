import time

from telebot import TeleBot

from src.config import BASE_DIR
from src.core import DatabaseClient, logger
from src.entities import BaseEntity
from src.services import BotService, Repository
from src.utils import YamlUtil


class Application:
    """运行类"""

    def __init__(self):
        self.config = YamlUtil(BASE_DIR / 'config.yaml')
        self.bot = TeleBot(self.config.get('bot', 'dev_token'))

        self.db: DatabaseClient | None = None
        self._setup()
        self.session = self.db.get_session()
        self.repo = Repository(self.session)
        self.service = BotService(self.bot, self.repo)

        logger.info('初始化成功')

    def __del__(self):
        self.session.close()  # 关闭数据库会话
        logger.info('已关闭数据库会话')

    def _setup(self) -> None:
        """初始化"""
        db_file_path = BASE_DIR / 'db' / 'data.db'
        db_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = DatabaseClient(f'sqlite:///{db_file_path}')
        BaseEntity.metadata.create_all(self.db.engine)

    def execute(self) -> None:
        """执行"""
        # 将某个频道的消息发送到群组对应的话题
        forward_mapping: dict = self.config.get('forward_mapping')
        # 获取最新的记录
        messages_dict: dict[str, list[int]] = self.service.check_channel_messages(list(forward_mapping.keys()))
        self.session.commit()
        logger.info(f'获取到 {sum([len(i) for i in messages_dict.values()])} 条消息')

        group_chat_id = self.config.get('group_chat_id')
        for channel_id, urls in messages_dict.items():
            # 开始转发
            channel_title = self.service.get_channel_title(int(channel_id))
            for url in urls:
                self.service.send_message_to_group(
                    html_text=f'#{channel_title} <a href="{url}">{url}</a>',
                    group_chat_id=group_chat_id,
                    message_thread_id=forward_mapping[channel_id]
                )
                time.sleep(3)
            logger.info(f'已转发 {channel_title} 的 {len(urls)} 条消息')
