from sqlalchemy import create_engine, Column, Integer, String, DateTime, BigInteger, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = f"sqlite:///{os.getenv('DB_PATH')}"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String)
    industry = Column(String)  # например: "автосервис", "промышленность", "сельхоз"
    telegram_username = Column(String)  # @username из Telegram
    created_at = Column(DateTime, default=datetime.utcnow)

class UserQuery(Base):
    __tablename__ = "user_queries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False)  # Telegram chat_id
    username = Column(String)  # @username
    query_text = Column(String, nullable=False)
    response_text = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_lead = Column(Boolean, default=False)  # был ли после этого лид?


# Создаём папку и БД при старте
os.makedirs(os.path.dirname(os.getenv("DB_PATH")), exist_ok=True)
Base.metadata.create_all(bind=engine)
