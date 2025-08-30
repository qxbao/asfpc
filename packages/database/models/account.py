"""Account model"""
from datetime import datetime
from typing import TYPE_CHECKING, List
from pydantic import BaseModel, Field
import ua_generator
from ua_generator.data.version import VersionRange
import ua_generator.options
from zendriver.cdp.network import CookieParam
from sqlalchemy import Dialect, ForeignKey, Integer, String, Boolean, DateTime, TypeDecorator
from sqlalchemy.orm import mapped_column, Mapped, relationship
import sqlalchemy
from .base import Base

if TYPE_CHECKING:
  from .proxy import Proxy
  from .group import Group
  from .user_profile import UserProfile

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

  def process_bind_param(self, value: CookieParam | None, dialect: Dialect) -> dict | None:  # noqa: PLR6301
    return value.to_json() if value else None

  def process_result_value(self, value: dict | None, dialect: Dialect) -> CookieParam | None:  # noqa: PLR6301
    return CookieParam.from_json(value) if value else None


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
  cookies: Mapped[CookieParam | None] = mapped_column(CookieType, nullable=True, default=None)
  access_token: Mapped[str] = mapped_column(String, default=None, nullable=True)
  proxy_id: Mapped[int | None] = mapped_column(ForeignKey("proxy.id"), nullable=True, default=None)
  proxy: Mapped["Proxy | None"] = relationship(back_populates="accounts")
  groups: Mapped[List["Group"]] = relationship(back_populates="account", cascade="all")
  scraped_profiles: Mapped[List["UserProfile"]] = relationship(back_populates="scraped_by_account", cascade="all")
  
  def to_schema(self) -> AccountSchema:
    """Convert the Account object to an AccountSchema."""
    return AccountSchema.model_validate(self)
    
  def to_json(self) -> dict:
    """Convert the Account object to a JSON serializable dictionary."""
    return AccountSchema.model_validate(self).model_dump()