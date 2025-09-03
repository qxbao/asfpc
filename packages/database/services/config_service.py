import logging
import os
from sqlalchemy import Sequence, select
from packages.database.database import Database
from packages.database.models.config import Config


class ConfigService:
  logger = logging.getLogger("ConfigService")
  def __init__(self):
    self.__session = Database.get_session()

  async def load_config_to_env(self) -> bool:
    async with self.__session as conn:
      configs: Sequence[Config] = (await conn.execute(
        select(Config)
      )).scalars().all()
      
      for config in configs:
        ConfigService.logger.info("Loading config %s = %s", config.key, config.value)
        os.environ[config.key] = config.value
      return True

  @staticmethod
  def get_config(config_name: str) -> str | None:
    if not os.environ or config_name not in os.environ:
      ConfigService.logger.error("Config '%s' not found", config_name)
      return None
    return os.environ[config_name]