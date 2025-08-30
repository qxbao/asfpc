"""User Profile model for storing Facebook profile data"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import ForeignKey, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import mapped_column, Mapped, relationship
from pydantic import BaseModel
from .base import Base

if TYPE_CHECKING:
    from .account import Account
    from .financial_analysis import FinancialAnalysis


class UserProfile(Base):
    """User Profile model for storing scraped Facebook profile data"""
    __tablename__ = "user_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    facebook_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    work: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    education: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    relationship_status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    profile_url: Mapped[str] = mapped_column(String, nullable=False)
    profile_picture_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    posts_sample: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    friends_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_scraped: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now
    )
    
    # Foreign key to account that scraped this profile
    scraped_by_account_id: Mapped[int] = mapped_column(
        ForeignKey("account.id"),
        nullable=False
    )
    scraped_by_account: Mapped["Account"] = relationship(back_populates="scraped_profiles")
    
    # Relationship to financial analysis
    financial_analyses: Mapped[list["FinancialAnalysis"]] = relationship(
        back_populates="user_profile",
        cascade="all, delete-orphan"
    )

    def to_schema(self) -> "UserProfileSchema":
        """Convert to schema"""
        return UserProfileSchema.model_validate(self)

    def to_json(self) -> dict:
        """Convert to JSON serializable dict"""
        return UserProfileSchema.model_validate(self).model_dump()


class UserProfileSchema(BaseModel):
    """Schema for UserProfile model"""
    id: int
    facebook_id: str
    name: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    work: Optional[str] = None
    education: Optional[str] = None
    relationship_status: Optional[str] = None
    profile_url: str
    profile_picture_url: Optional[str] = None
    posts_sample: Optional[str] = None
    friends_count: Optional[int] = None
    is_verified: bool = False
    last_scraped: datetime
    created_at: datetime
    updated_at: datetime
    scraped_by_account_id: int

    model_config = {"from_attributes": True}


class UserProfileCreateDTO(BaseModel):
    """Data Transfer Object for creating a new user profile"""
    facebook_id: str
    name: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    work: Optional[str] = None
    education: Optional[str] = None
    relationship_status: Optional[str] = None
    profile_url: str
    profile_picture_url: Optional[str] = None
    posts_sample: Optional[str] = None
    friends_count: Optional[int] = None
    is_verified: bool = False