from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine
from typing import Optional
from urllib.parse import quote
import logging
from .models.base import Base

class Database:
  __engine: Optional[AsyncEngine] = None
  __session: Optional[async_sessionmaker[AsyncSession]] = None
  logger = logging.getLogger("Database")
  
  @staticmethod
  async def init(
    username: str,
    password: str,
    host: str,
    db: str = "asfpc"
  ) -> bool:
    try:
      connection_str: str = f"postgresql+asyncpg://{username}:{quote(password)}@{host}/{db}"
      connection_str_hidden: str = f"postgresql+asyncpg://{username}:{"*" * len(password)}@{host}/{db}"
      # Init engine
      Database.logger.info(f"Initializing database connection to {connection_str_hidden}")
      Database.__engine = create_async_engine(connection_str)
      # Init session
      Database.__session = async_sessionmaker(bind=Database.__engine)

      async with Database.__engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
      return True
    except Exception as e:
      Database.logger.error(f"Error initializing database: {e}")
      return False

  @staticmethod
  def get_engine() -> AsyncEngine:
    if not Database.__engine:
      Database.logger.exception("Database engine is not initialized.")
      raise Exception("Database engine is not initialized.")
    return Database.__engine

  @staticmethod
  def get_session() -> AsyncSession:
    if not Database.__session:
      Database.logger.exception("Database session is not initialized.")
      raise Exception("Database session is not initialized.")
    return Database.__session()
  
  @staticmethod
  async def close():
    if Database.__session:
      async with Database.__session() as session:
        await session.close()
    if Database.__engine:
      await Database.__engine.dispose()