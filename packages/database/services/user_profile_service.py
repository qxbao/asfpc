"""Service for managing UserProfile entities"""
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from ..database import Database
from ..models.user_profile import UserProfile, UserProfileCreateDTO
import logging

class UserProfileService:
    """Service for managing UserProfile entities"""

    def __init__(self):
        self.__session = Database.get_session()
        self.logger = logging.getLogger("UserProfileService")

    async def create_profile(self, profile_data: UserProfileCreateDTO, account_id: int) -> UserProfile:
        """Create a new user profile
        
        Args:
            profile_data: Profile data to create
            account_id: ID of the account that scraped this profile
            
        Returns:
            UserProfile: The created profile
        """
        async with self.__session as conn:
            profile = UserProfile(
                **profile_data.model_dump(),
                scraped_by_account_id=account_id
            )
            conn.add(profile)
            await conn.commit()
            await conn.refresh(profile)
            conn.expunge(profile)
            return profile

    async def get_profile_by_facebook_id(self, facebook_id: str) -> Optional[UserProfile]:
        """Get profile by Facebook ID
        
        Args:
            facebook_id: Facebook user ID
            
        Returns:
            Optional[UserProfile]: Profile if found
        """
        async with self.__session as conn:
            result = await conn.execute(
                select(UserProfile)
                .options(selectinload(UserProfile.financial_analyses))
                .where(UserProfile.facebook_id == facebook_id)
            )
            return result.scalar_one_or_none()

    async def get_profile_by_id(self, profile_id: int) -> Optional[UserProfile]:
        """Get profile by ID
        
        Args:
            profile_id: Profile ID
            
        Returns:
            Optional[UserProfile]: Profile if found
        """
        async with self.__session as conn:
            result = await conn.execute(
                select(UserProfile)
                .options(selectinload(UserProfile.financial_analyses))
                .where(UserProfile.id == profile_id)
            )
            return result.scalar_one_or_none()

    async def get_profiles_by_ids(self, profile_ids: List[int]) -> List[UserProfile]:
        """Get multiple profiles by IDs
        
        Args:
            profile_ids: List of profile IDs
            
        Returns:
            List[UserProfile]: Found profiles
        """
        async with self.__session as conn:
            result = await conn.execute(
                select(UserProfile)
                .options(selectinload(UserProfile.financial_analyses))
                .where(UserProfile.id.in_(profile_ids))
            )
            return list(result.scalars().all())

    async def update_profile(self, profile: UserProfile) -> None:
        """Update a profile
        
        Args:
            profile: Profile to update
        """
        async with self.__session as conn:
            profile.updated_at = datetime.now()
            await conn.merge(profile)
            await conn.commit()

    async def is_profile_stale(self, facebook_id: str, max_age_hours: int = 24) -> bool:
        """Check if profile needs re-scraping
        
        Args:
            facebook_id: Facebook user ID
            max_age_hours: Maximum age in hours before profile is considered stale
            
        Returns:
            bool: True if profile needs re-scraping
        """
        profile = await self.get_profile_by_facebook_id(facebook_id)
        if not profile:
            return True
            
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        return profile.last_scraped < cutoff_time

    async def get_recent_profiles(self, account_id: Optional[int] = None, limit: int = 100) -> List[UserProfile]:
        """Get recently scraped profiles
        
        Args:
            account_id: Optional account ID to filter by
            limit: Maximum number of profiles to return
            
        Returns:
            List[UserProfile]: Recent profiles
        """
        async with self.__session as conn:
            query = select(UserProfile).order_by(UserProfile.last_scraped.desc()).limit(limit)
            
            if account_id:
                query = query.where(UserProfile.scraped_by_account_id == account_id)
            
            result = await conn.execute(query)
            return list(result.scalars().all())

    async def get_profiles_needing_analysis(self, limit: int = 10) -> List[UserProfile]:
        """Get profiles that need financial analysis
        
        Args:
            limit: Maximum number of profiles to return
            
        Returns:
            List[UserProfile]: Profiles needing analysis
        """
        async with self.__session as conn:
            # Get profiles that have no financial analysis or old analysis
            cutoff_time = datetime.now() - timedelta(days=7)  # Re-analyze after 7 days
            
            result = await conn.execute(
                select(UserProfile)
                .options(selectinload(UserProfile.financial_analyses))
                .where(
                    and_(
                        UserProfile.bio.is_not(None),  # Only analyze profiles with bio
                        # Either no analysis or old analysis
                        ~UserProfile.financial_analyses.any() |
                        ~UserProfile.financial_analyses.any(
                            UserProfile.financial_analyses.any(
                                UserProfile.financial_analyses.any().created_at > cutoff_time
                            )
                        )
                    )
                )
                .limit(limit)
            )
            return list(result.scalars().all())