import logging
from typing import List
from packages.database.database import Database
from packages.database.models.post import Post

class PostService:
  def __init__(self):
    self.__session = Database.get_session()
    self.logger = logging.getLogger("PostService")

  async def insert_posts(self, posts: List[Post], ignore_errors: bool = False) -> int:
    success_count = 0
    for post in posts:
      try:
        await self.insert_post(post)
        success_count += 1
      except Exception as e:
        self.logger.exception(e)
        if not ignore_errors:
          raise RuntimeError("Failed to insert posts: " + str(e))
    return success_count

  async def insert_post(self, post: Post):
    async with self.__session as conn:
      conn.add(post)
      await conn.commit()
      await conn.refresh(post)
      conn.expunge(post)