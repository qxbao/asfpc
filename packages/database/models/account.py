from datetime import datetime
from typing import List
from sqlalchemy import Integer, String, Boolean, DateTime
import ua_generator
from sqlalchemy.orm import mapped_column, Mapped, relationship
from .base import Base
from .proxy import Proxy

UA_OPTS = ua_generator._options.Options(
  weighted_versions=True,
  version_ranges={
    "chrome": ua_generator._options.VersionRange(min="134.0", max="138.0"),
  }
)

def gen_ua() -> str:
  return ua_generator.generate(
    browser="chrome", platform="windows", device="desktop", options=UA_OPTS
  ).text

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
    proxy: Mapped[List["Proxy"]] = relationship(back_populates="accounts")
