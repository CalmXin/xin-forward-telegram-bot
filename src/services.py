import re
from concurrent.futures.thread import ThreadPoolExecutor

import httpx
import telebot
from sqlalchemy.orm import Session
from telebot import TeleBot

from src.core import logger
from src.entities import MessagesEntity
from src.utils import get_channel_url_by_username


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
    def __init__(self, bot: TeleBot):
        self._bot = bot

    def get_channel_title(self, channel_id: int) -> str:
        """
        获取频道的标题
        """
        channel = self._bot.get_chat(channel_id)
        return channel.title

    def get_channel_username(self, channel_id: int) -> str | None:
        """
        获取频道的用户名
        """
        try:
            channel = self._bot.get_chat(channel_id)
            return channel.username
        except telebot.apihelper.ApiTelegramException as e:
            return None

    def check_one_channel_message(self, channel_id: int) -> dict:
        """
        获取单个频道的更新

        :return: key 为频道的 ID，value 是数组，代表最新的消息 ID
        """
        result = {}
        # 获取更新
        channel_username = self.get_channel_username(channel_id)
        response = httpx.get(f'https://t.me/s/{channel_username}')
        html_text = response.text
        message_ids = re.findall(rf'https://t.me/{channel_username}/(\d+)', html_text)
        result[channel_id] = message_ids
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


class CheckService:
    def __init__(self, repo: Repository, bot_service: BotService, pool: ThreadPoolExecutor):
        self.repo = repo
        self.bot_service = bot_service
        self.pool = pool

    def check_channel_messages(self, channel_id_list: list[int]) -> dict:
        """
        获取所有频道的更新

        :return: key 为频道的 ID，value 是数组，代表最新的消息 ID
        """
        results = self.pool.map(self._fetch_one_channel_message, channel_id_list)
        return {
            k: v
            for result in results if result
            for k, v in result.items() if v
        }

    def _fetch_one_channel_message(self, channel_id: int) -> dict[int, list[str]] | None:
        """获取单个频道的所有新链接"""
        result = []  # 用于储存所有的 url

        # 判断频道是否是需要被收集的
        channel_username = self.bot_service.get_channel_username(channel_id)
        if channel_username is None:
            logger.warning(f"频道 {channel_id} 不是公开频道")
            return None

        one_channel_result = self.bot_service.check_one_channel_message(channel_id)  # 获取单个频道的更新
        for message_id in one_channel_result[channel_id]:
            # 检测是否在数据库中
            if self.repo.check_message(channel_id, message_id):
                continue
            # 生成消息链接
            url = get_channel_url_by_username(channel_username, message_id)
            # 保存结果
            result.append(url)
            # 保存到数据库
            self.repo.save_message(channel_id, message_id, url)
        return {channel_id: result}
