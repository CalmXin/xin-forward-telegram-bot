from sqlalchemy.orm import Session
from telebot import TeleBot

from src.entities import MessagesEntity
from src.utils import get_channel_url_by_username, get_channel_url_by_id


class Repository:
    def __init__(self, session: Session | None = None):
        self.session = session

    def save_message(self, channel_id, message_id: int, message_url: str):
        """保存消息"""
        self.session.add(
            MessagesEntity(
                channel_id=channel_id,
                message_id=message_id,
                message_url=message_url
            )
        )

    def get_latest_id(self, channel_id: int) -> int:
        """获取最新的消息 ID"""
        result = (
            self.session.query(MessagesEntity.message_id)
            .filter(MessagesEntity.channel_id == channel_id)
            .order_by(MessagesEntity.message_id.desc())
            .first()
        )
        return result[0] if result else 0

    def check_message(self, channel_id: int, message_id: int) -> bool:
        """检查消息是否已经保存"""
        result = (
            self.session.query(MessagesEntity)
            .filter(MessagesEntity.channel_id == channel_id)
            .filter(MessagesEntity.message_id == message_id)
            .first()
        )
        return result is not None


class BotService:
    def __init__(self, bot: TeleBot, repo: Repository | None = None):
        self._bot = bot
        self.repo = repo

    def get_channel_title(self, channel_id: int) -> str:
        """
        获取频道的标题
        """
        channel = self._bot.get_chat(channel_id)
        return channel.title

    def get_channel_username(self, channel_id: int) -> str:
        """
        获取频道的标题
        """
        channel = self._bot.get_chat(channel_id)
        return channel.username

    def check_channel_messages(self) -> dict:
        """
        获取所有频道的更新

        :return: key 为频道的 ID，value 是数组，代表最新的消息 ID
        """
        result = {}
        # 获取更新
        updates = self._bot.get_updates(timeout=10, allowed_updates=["channel_post"])

        for update in updates:
            # 不是频道消息跳过
            if update.channel_post is None:
                continue
            # 提取信息
            channel_post = update.channel_post
            message_id = channel_post.message_id
            channel_id = channel_post.chat.id
            # > 检测是否在数据库中
            if not self.repo.check_message(channel_id, message_id):
                continue
            # > 如果频道 ID 不在结果中，则创建一个空数组
            if channel_id not in result:
                result[channel_id] = []
            channel_username = self.get_channel_username(channel_id)

            # 生成消息链接
            if channel_username is not None:
                url = get_channel_url_by_username(channel_username, message_id)
            else:
                url = get_channel_url_by_id(channel_id, message_id)

            # 保存结果
            result[channel_id].append(url)
            # 保存到数据库
            self.repo.save_message(channel_id, message_id, url)
        return result

    def send_message_to_group(self, html_text: str, group_chat_id: int, message_thread_id: int) -> None:
        """
        将消息发送到话题群组
        """
        self._bot.send_message(
            group_chat_id,
            html_text,
            parse_mode="html",
            message_thread_id=message_thread_id
        )
