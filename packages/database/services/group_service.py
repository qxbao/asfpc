"""Service for managing groups."""
import logging
from datetime import datetime
from typing import List
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from packages.database.database import Database
from packages.database.models.account import Account
from packages.database.models.group import Group
from packages.database.models.post import Post
from packages.database.services.config_service import ConfigService
from packages.sns_utils.fgraph import FacebookGraph


class GroupService:
  def __init__(self):
    self.__session = Database.get_session()
    self.logger = logging.getLogger("GroupService")

  async def get_group_by_id(self, group_id: int) -> Group | None:
    try:
      return await self.__session.get(Group, group_id)
    except Exception as e:
      self.logger.exception(e)
      return None

  async def get_group_by_gid(self, group_gid: str, lazyload: bool = False) -> Group | None:
    try:
      async with self.__session as conn:
        query = select(Group).where(Group.group_id == group_gid)
        if lazyload:
          query = query.options(selectinload(Group.account))
        res = await conn.execute(
          query
        )
        return res.scalar_one_or_none()
    except Exception as e:
      self.logger.exception(e)
      raise RuntimeError("Failed to retrieve group by GID: " + str(e))

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
    
  async def scan_group(self, group_id: str) -> List[Post]:
    group = await self.get_group_by_gid(group_id, True)
    if not group:
      raise RuntimeError("Group not found")
    graph = FacebookGraph()
    fetch_limit = ConfigService.get_config("FB_POST_FETCH_LIMIT")
    self.logger.info(group.account.access_token)
    response = graph.get_posts_from_group(
      group,
      limit=int(fetch_limit) if fetch_limit else 20,
      order="chronological",
      access_token=group.account.access_token
    )
    posts: List[Post] = []
    print(response)
    for post_data in response.data:
      post_id = post_data.id.split("_")[-1]
      post = Post(
        post_id=post_id,
        group=group,
        content=post_data.message if post_data.message else "",
        created_at=datetime.fromisoformat(post_data.updated_time).replace(tzinfo=None)
      )
      posts.append(post)
    return posts