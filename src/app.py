import time
from concurrent.futures.thread import ThreadPoolExecutor

from telebot import TeleBot

from src.config import BASE_DIR
from src.core import DatabaseClient, logger
from src.entities import BaseEntity
from src.services import BotService, Repository, CheckService
from src.utils import YamlUtil


class Application:
    """运行类"""

    def __init__(self):
        self.config = YamlUtil(BASE_DIR / 'config.yaml')
        self.bot = TeleBot(self.config.get('bot', 'token'))

        self.db: DatabaseClient | None = None
        self._setup()
        self.bot_service = BotService(self.bot)
        self.pool = ThreadPoolExecutor(max_workers=10)
        logger.info('初始化成功')

    def __del__(self):
        self.pool.shutdown(wait=False)
        logger.info('已关闭线程池')

    def _setup(self) -> None:
        """初始化"""
        db_file_path = BASE_DIR / 'db' / 'data.db'
        db_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = DatabaseClient(f'sqlite:///{db_file_path}')
        BaseEntity.metadata.create_all(self.db.engine)
        logger.info('已初始化数据库')

    def execute(self) -> None:
        """执行"""
        # 将某个频道的消息发送到群组对应的话题
        forward_mapping: dict = self.config.get('forward_mapping')
        # 获取最新的记录
        session = self.db.get_session()
        try:
            check_service = CheckService(Repository(session), self.bot_service, self.pool)
            with session.begin():
                messages_dict: dict[str, list[int]] = check_service.check_channel_messages(
                    list(forward_mapping.keys())
                )
            logger.info(f'获取到 {sum([len(i) for i in messages_dict.values()])} 条消息')
        finally:
            session.close()

        # 开始转发
        group_chat_id = self.config.get('group_chat_id')
        for channel_id, urls in messages_dict.items():
            # 开始转发
            channel_username = self.bot_service.get_channel_username(int(channel_id))
            for url in urls:
                self.bot_service.send_message_to_group(
                    html_text=f'#{channel_username} <a href="{url}">{url}</a>',
                    group_chat_id=group_chat_id,
                    message_thread_id=forward_mapping[channel_id]
                )
                logger.info(f'已转发 {channel_username} 的 {url}')
                time.sleep(3)
            logger.info(f'已转发 {channel_username} 的 {len(urls)} 条消息')
