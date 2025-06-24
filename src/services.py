import re
from concurrent.futures.thread import ThreadPoolExecutor

import httpx
import telebot
from sqlalchemy.orm import Session
from telebot import TeleBot

from src.core import logger
from src.entities import MessagesEntity
from src.utils import get_channel_url_by_username


def get_username_by_url(url: str) -> str | None:
    """获取频道的用户名"""
    match = re.match(r"https://t.me/([\w_]+)", url)
    if match:
        return match.group(1)
    else:
        return None


class Repository:
    def __init__(self, session: Session | None = None):
        self.session = session

    def save_message(self, channel_id: int, message_id: int, message_url: str):
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

    def get_all_not_send_messages(self) -> dict[str, list[str]]:
        """获取所有未发送的消息，格式为 dict[channel_username, urls]"""
        urls = (
            self.session.query(MessagesEntity.message_url)
            .filter(MessagesEntity.is_send == False)
            .all()
        )
        return {
            get_username_by_url(url[0]): [url[0]]
            for url in urls
        }

    def mark_url_is_send(self, url: str) -> None:
        """将消息标记为已发送"""
        self.session.query(MessagesEntity).filter(MessagesEntity.message_url == url).update({
            MessagesEntity.is_send: True
        })


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
        except telebot.apihelper.ApiTelegramException:
            return None

    def get_channel_id(self, channel_username: str) -> int | None:
        """
        获取频道的 ID
        """
        try:
            channel = self._bot.get_chat(f"@{channel_username}")
            return channel.id
        except telebot.apihelper.ApiTelegramException as e:
            logger.warning(f"频道 {channel_username} 获取 ID 出错，{e}")
            return None

    def check_one_channel_message(self, channel_username: str) -> list[int]:
        """
        获取单个频道的更新

        :return: key 为频道的 ID，value 是数组，代表最新的消息 ID
        """
        # 获取更新
        response = httpx.get(f'https://t.me/s/{channel_username}')
        html_text = response.text
        message_ids = re.findall(rf'https://t.me/{channel_username}/(\d+)', html_text)
        return [int(message_id) for message_id in message_ids]

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

    def check_channel_messages(self, channel_username_list: list[str]) -> dict[int, list[str]]:
        """
        获取所有频道的更新

        :return: key 为频道的 ID，value 是数组，代表最新的消息 ID
        """
        results = self.pool.map(self._fetch_one_channel_message, channel_username_list)
        return {
            k: v
            for result in results if result
            for k, v in result.items() if v
        }

    def _fetch_one_channel_message(self, channel_username: str) -> dict[int, list[str]]:
        """获取单个频道的所有新链接"""
        result = []  # 用于储存所有的 url
        # 判断频道是否是需要被收集的
        channel_id = self.bot_service.get_channel_id(channel_username)
        if channel_id is None:
            logger.warning(f"频道 {channel_username} 不是公开频道")
            return {}

        try:
            one_channel_result = self.bot_service.check_one_channel_message(channel_username)  # 获取单个频道的更新
        except httpx.HTTPError:
            logger.warning(f"频道 {channel_username} 获取更新失败")
            return {}

        for message_id in one_channel_result:
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
