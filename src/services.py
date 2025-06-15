from telebot import TeleBot

from src.utils import get_channel_url_by_username, get_channel_url_by_id


class BotService:
    def __init__(self, bot: TeleBot):
        self._bot = bot

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
        updates = self._bot.get_updates(timeout=10, allowed_updates=["channel_post"])
        for update in updates:
            # 不是频道消息跳过
            if update.channel_post is None:
                continue
            channel_post = update.channel_post
            message_id = channel_post.message_id
            channel_id = channel_post.chat.id
            if channel_id not in result:
                result[channel_id] = []
            channel_username = self.get_channel_username(channel_id)
            if channel_username is not None:
                result[channel_id].append(get_channel_url_by_username(channel_username, message_id))
            else:
                result[channel_id].append(get_channel_url_by_id(channel_id, message_id))
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
