from typing import TYPE_CHECKING, List
from pydantic import BaseModel
from sqlalchemy import Column, ForeignKey, Table
from .base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
  from .account import Account
  from .post import Post

account_group_table = Table(
    "account_group_association",
    Base.metadata,
    Column("account_id", ForeignKey("account.id"), primary_key=True),
    Column("group_id", ForeignKey("group.id"), primary_key=True),
)

class GroupSchema(BaseModel):
  """Schema for Group model."""
  id: int
  group_id: str
  group_name: str
  is_joined: bool
  model_config = {"from_attributes": True}

class Group(Base):
  __tablename__ = "group"
  id: Mapped[int] = mapped_column(primary_key=True)
  group_id: Mapped[str] = mapped_column(nullable=False)
  group_name: Mapped[str] = mapped_column(nullable=False)
  is_joined: Mapped[bool] = mapped_column(default=False)
  accounts: Mapped[List["Account"]] = relationship(
    secondary=account_group_table,
    back_populates="groups")
  posts: Mapped[list["Post"]] = relationship(back_populates="group")
  
  def to_schema(self) -> GroupSchema:
    """Convert the Group object to GroupSchema"""
    return GroupSchema.model_validate(self)
  
  def to_json(self) -> dict:
    """Convert the Group object to a JSON-serializable dictionary."""
    return GroupSchema.model_validate(self).model_dump()