"""Service for managing groups."""
import logging
from sqlalchemy import select
from packages.database.database import Database
from packages.database.models.account import Account
from packages.database.models.group import Group


class GroupService:
  def __init__(self):
    self.__session = Database.get_session()
    self.logger = logging.getLogger("GroupService")

  async def get_group_by_id(self, group_id: int) -> Group | None:
    try:
      group = await self.__session.get(Group, group_id)
      return group
    except Exception as e:
      self.logger.exception(e)
      return None

  async def update_group(self, group: Group) -> None:
    async with self.__session as conn:
      conn.add(group)
      await conn.commit()
      await conn.refresh(group)
      conn.expunge(group)

  async def link_group(self,
      account: Account,
      group_id: str,
      group_name: str,
      is_joined: bool=False) -> Group:
    try:
      async with self.__session as conn:
        account = await conn.merge(account)
        group = (await conn.execute(
          select(Group).where(
            Group.group_id == group_id,
            Group.group_name == group_name,
          )
        )).scalar_one_or_none()
        if not group:
          group = Group(
            group_name=group_name,
            group_id=group_id,
            is_joined=is_joined
          )
        group.account = account
        self.__session.add(group)
        await self.__session.commit()
        await self.__session.refresh(group)
        return group
    except Exception as e:
      self.logger.exception(e)
      await self.__session.rollback()
      raise RuntimeError(e)