from typing import TYPE_CHECKING
from .base import Base
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

if TYPE_CHECKING:
  from .post import Post

class Comment(Base):
  __tablename__ = "comment"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  content: Mapped[str] = mapped_column(String, nullable=False)
  is_analyzed: Mapped[bool] = mapped_column(default=False)
  created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
  inserted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
  post_id: Mapped[int] = mapped_column(ForeignKey("post.id"), nullable=False)
  post: Mapped["Post"] = relationship(back_populates="comments")