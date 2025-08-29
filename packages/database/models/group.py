from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey
from .base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
  from .account import Account
  from .post import Post

class Group(Base):
  __tablename__ = "group"
  id: Mapped[int] = mapped_column(primary_key=True)
  group_id: Mapped[str] = mapped_column(unique=True, nullable=False)
  group_name: Mapped[str] = mapped_column(nullable=False)
  is_joined: Mapped[bool] = mapped_column(default=False)
  account_id: Mapped[int] = mapped_column(ForeignKey("account.id"))
  account: Mapped["Account"] = relationship(back_populates="groups")
  posts: Mapped[list["Post"]] = relationship(back_populates="group")