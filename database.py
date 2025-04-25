#database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, func, BigInteger
from config import DB_URL
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    user_id = Column(BigInteger, primary_key=True)
    messages_today = Column(Integer, default=0)
    last_message_date = Column(DateTime, default=func.now())
    subscription_until = Column(DateTime, default=None)

engine = create_async_engine(DB_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
