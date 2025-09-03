from packages.database.database import Database
from packages.database.models.comment import Comment


class CommentService:
  def __init__(self):
    self.__session = Database.get_session()

  async def insert_comment(self, comment: Comment):
    async with self.__session() as session:
      session.add(comment)
      await session.commit()
      await session.refresh(comment)
      
  async def insert_comments(self, comments: list[Comment], ignore_errors: bool = False) -> int:
    for comment in comments:
      try:
        await self.insert_comment(comment)
      except Exception as e:
        if not ignore_errors:
          raise RuntimeError("Failed to insert comments: " + str(e))
    return len(comments)
  
  