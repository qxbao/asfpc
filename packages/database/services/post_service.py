import logging
from typing import List
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from packages.database.database import Database
from packages.database.models.group import Group
from packages.database.models.comment import Comment
from packages.database.models.post import Post
from packages.database.models.profile import UserProfile
from packages.database.services.account_service import AccountService
from packages.database.services.config_service import ConfigService
from packages.sns_utils.fgraph import FacebookGraph

class PostService:
  def __init__(self):
    self.__session = Database.get_session()
    self.logger = logging.getLogger("PostService")
    
  async def get_post_by_pid(self, pid: str, lazy: bool = False) -> Post | None:
    async with self.__session as conn:
      query = select(Post).where(Post.post_id == pid)
      if lazy:
        query = query.options(
          selectinload(Post.group).selectinload(Group.account)
        )
      result = await conn.execute(
        query
      )
      return result.scalar_one_or_none()

  async def update_post(self, post: Post):
    async with self.__session as conn:
      await conn.merge(post)
      await conn.commit()

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

  async def scan_post(self, post_id: str) -> List[Comment]:
    post = await self.get_post_by_pid(post_id, lazy=True)
    if not post:
      raise RuntimeError(f"Post with ID {post_id} not found.")
    graph = FacebookGraph()
    access_token = post.group.account.access_token
    if not access_token:
      access_token = await AccountService.gen_access_token(post.group.account)
    fetch_limit = ConfigService.get_config("FB_COMMENT_FETCH_LIMIT")
    response = graph.get_posts_comments(
      post,
      limit=fetch_limit if fetch_limit else 20,
      order="chronological",
      access_token=access_token
    )
    comments: List[Comment] = []
    for comment_data in response.data:
      profile = UserProfile(
        facebook_id=comment_data.from_.get("id"),
        name=comment_data.from_.get("name"),
        profile_url=f"https://www.facebook.com/profile.php?id={comment_data.from_.get("id")}",
        scraped_by=post.group.account
      )
      comment = Comment(
        author=profile,
        comment_id=comment_data.id,
        post=post,
        content=comment_data.message,
        created_at=datetime.fromisoformat(comment_data.created_time).replace(tzinfo=None)
      )
      comments.append(comment)
    post.is_analyzed = True
    await self.update_post(post)
    return comments