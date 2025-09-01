"""Account model"""
import os
from datetime import datetime
from typing import TYPE_CHECKING, List
from pydantic import BaseModel, Field
import ua_generator
from ua_generator.data.version import VersionRange
import ua_generator.options
from zendriver.cdp.network import Cookie
from sqlalchemy import Dialect, ForeignKey, Integer, String, Boolean, DateTime, TypeDecorator
from sqlalchemy.orm import mapped_column, Mapped, relationship
import sqlalchemy
from .base import Base
from .group import account_group_table

if TYPE_CHECKING:
  from .proxy import Proxy
  from .group import Group

# User-Agent options
UA_OPTS = ua_generator.options.Options(
  weighted_versions=True,
  version_ranges={
    "chrome": VersionRange(min_version=134, max_version=138),
  }
)

def gen_ua() -> str:
  """Generate a user-agent string.

  Returns:
      str: The generated user-agent string.
  """
  return ua_generator.generate(
    browser="chrome", platform="windows", device="desktop", options=UA_OPTS
  ).text

class AccountSchema(BaseModel):
  """Schema for Account model."""
  id: int
  username: str
  email: str
  is_block: bool
  ua: str
  created_at: datetime
  updated_at: datetime
  model_config = {"from_attributes": True}

class AddAccountDTO(BaseModel):
  """Data Transfer Object for adding a new account."""
  username: str = Field(..., min_length=5, max_length=25, examples=["1000123456522"])
  email: str = Field(..., examples=["example@example.com"])
  password: str = Field(..., min_length=8, examples=["example_password"])

class CookieType(TypeDecorator):
  """Custom SQLAlchemy type for handling CookieParam objects."""
  impl = sqlalchemy.types.JSON

  def process_bind_param( # noqa: PLR6301
    self,
    value: List[Cookie] | None,
    dialect: Dialect
  ) -> list[dict] | None:
    return [cookie.to_json() for cookie in value] if value else None

  def process_result_value(self, value: dict | None, dialect: Dialect) -> List[Cookie] | None:  # noqa: PLR6301
    return [Cookie.from_json(cookie) for cookie in value] if value else None


class Account(Base):
  """Account model for the application."""
  __tablename__ = "account"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
  username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
  password: Mapped[str] = mapped_column(String, nullable=False)
  is_block: Mapped[bool] = mapped_column(Boolean, default=False)
  ua: Mapped[str] = mapped_column(String, default=gen_ua)
  created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
  updated_at: Mapped[datetime] = mapped_column(
    DateTime,
    default=datetime.now,
    onupdate=datetime.now
  )
  cookies: Mapped[list[Cookie]] = mapped_column(CookieType, nullable=True, default=None)
  access_token: Mapped[str] = mapped_column(String, default=None, nullable=True)
  proxy_id: Mapped[int | None] = mapped_column(ForeignKey("proxy.id"), nullable=True, default=None)
  proxy: Mapped["Proxy | None"] = relationship(back_populates="accounts")
  groups: Mapped[list["Group"]] = relationship(
    secondary=account_group_table,
    back_populates="accounts"
    )
  
  def to_schema(self) -> AccountSchema:
    """Convert the Account object to an AccountSchema."""
    return AccountSchema.model_validate(self)
    
  def to_json(self) -> dict:
    """Convert the Account object to a JSON serializable dictionary."""
    return AccountSchema.model_validate(self).model_dump()

  def get_user_data_dir(self) -> str:
    """Get the user data directory for the account.

    Returns:
        str: The user data directory path.
    """
    user_data_dir = os.path.join(os.getcwd(), "resources", "user_data_dir", str(self.id))
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)
    return user_data_dir