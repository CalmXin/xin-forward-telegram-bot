from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


class DatabaseClient:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.session_factory = sessionmaker(bind=self.engine)

    def get_session(self) -> Session:
        return self.session_factory()
