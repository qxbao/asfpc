from datetime import datetime
from typing import List, Literal
from pydantic import BaseModel
from sqlalchemy import Dialect, ForeignKey, Integer, String, Boolean, DateTime, TypeDecorator, null
import sqlalchemy
import ua_generator
from sqlalchemy.orm import mapped_column, Mapped, relationship
from .base import Base
from .proxy import Proxy
from ua_generator.data.version import VersionRange
from zendriver.cdp.network import CookieParam

UA_OPTS = ua_generator._options.Options(
  weighted_versions=True,
  version_ranges={
    "chrome": VersionRange(min_version=134, max_version=138),
  }
)

def gen_ua() -> str:
  return ua_generator.generate(
    browser="chrome", platform="windows", device="desktop", options=UA_OPTS
  ).text

class AccountSchema(BaseModel):
  id: int
  username: str
  email: str
  is_block: bool
  ua: str
  created_at: datetime
  updated_at: datetime
  
  model_config = {"from_attributes": True}

class CookieType(TypeDecorator):
  impl = sqlalchemy.types.JSON

  def process_bind_param(self, value: CookieParam | None, dialect: Dialect) -> dict | None:
    return value.to_json() if value else None

  def process_result_value(self, value: dict | None, dialect: Dialect) -> CookieParam | None:
    return CookieParam.from_json(value) if value else None


class Account(Base):
  __tablename__ = "account"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
  username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
  password: Mapped[str] = mapped_column(String, nullable=False)
  is_block: Mapped[bool] = mapped_column(Boolean, default=False)
  ua: Mapped[str] = mapped_column(String, default=lambda: gen_ua())
  created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
  updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
  cookies: Mapped[CookieParam | None] = mapped_column(CookieType, nullable=True, default=None)
  proxy_id: Mapped[int | None] = mapped_column(ForeignKey("proxy.id"), nullable=True, default=None)
  proxy: Mapped["Proxy | None"] = relationship(back_populates="accounts")
  
  def to_schema(self) -> AccountSchema:
    return AccountSchema.model_validate(self)
    