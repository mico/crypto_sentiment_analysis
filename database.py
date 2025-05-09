from sqlalchemy import Column, Integer, String, DateTime, Float, create_engine, Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from typing import Optional


Base = declarative_base()


class SentimentData(Base):  # type: ignore
    """SQLAlchemy model for sentiment data table."""

    __tablename__ = 'sentiment_data'

    index = Column(Integer)
    id = Column(String, primary_key=True)
    domain = Column(String)
    title = Column(String)
    coins = Column(String, index=True)
    published_at = Column(DateTime, index=True)
    url = Column(String)
    sentiment = Column(Float, index=True)


def get_engine(db_path: str = 'crypto_data.db') -> Engine:
    """Create SQLAlchemy engine instance."""
    return create_engine(f'sqlite:///{db_path}')


def get_session(engine: Optional[Engine] = None) -> Session:
    """Create a new Session."""
    if engine is None:
        engine = get_engine()
    Session = scoped_session(sessionmaker(bind=engine))
    return Session()


def init_db(engine: Optional[Engine] = None) -> None:
    """Create all tables in the database."""
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)
