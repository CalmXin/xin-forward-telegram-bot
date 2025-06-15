from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.orm import declarative_base

from src.utils import utcnow

BaseEntity = declarative_base()


class MessagesEntity(BaseEntity):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(Integer)
    message_id = Column(Integer)
    create_time = Column(DateTime(timezone=True), default=utcnow)
    update_time = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
