"""Service for managing FinancialAnalysis entities"""
from typing import List, Optional
from sqlalchemy import select
from ..database import Database
from ..models.financial_analysis import FinancialAnalysis, FinancialAnalysisCreateDTO
import logging

class FinancialAnalysisService:
    """Service for managing FinancialAnalysis entities"""

    def __init__(self):
        self.__session = Database.get_session()
        self.logger = logging.getLogger("FinancialAnalysisService")

    async def create_analysis(
        self, 
        analysis_data: FinancialAnalysisCreateDTO, 
        user_profile_id: int
    ) -> FinancialAnalysis:
        """Create a new financial analysis
        
        Args:
            analysis_data: Analysis data to create
            user_profile_id: ID of the user profile this analysis belongs to
            
        Returns:
            FinancialAnalysis: The created analysis
        """
        async with self.__session as conn:
            analysis = FinancialAnalysis(
                **analysis_data.model_dump(),
                user_profile_id=user_profile_id
            )
            conn.add(analysis)
            await conn.commit()
            await conn.refresh(analysis)
            conn.expunge(analysis)
            return analysis

    async def get_analysis_by_id(self, analysis_id: int) -> Optional[FinancialAnalysis]:
        """Get analysis by ID
        
        Args:
            analysis_id: Analysis ID
            
        Returns:
            Optional[FinancialAnalysis]: Analysis if found
        """
        async with self.__session as conn:
            result = await conn.execute(
                select(FinancialAnalysis).where(FinancialAnalysis.id == analysis_id)
            )
            return result.scalar_one_or_none()

    async def get_latest_analysis_for_profile(
        self, 
        user_profile_id: int
    ) -> Optional[FinancialAnalysis]:
        """Get the latest analysis for a user profile
        
        Args:
            user_profile_id: User profile ID
            
        Returns:
            Optional[FinancialAnalysis]: Latest analysis if found
        """
        async with self.__session as conn:
            result = await conn.execute(
                select(FinancialAnalysis)
                .where(FinancialAnalysis.user_profile_id == user_profile_id)
                .order_by(FinancialAnalysis.created_at.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def get_analyses_for_profile(self, user_profile_id: int) -> List[FinancialAnalysis]:
        """Get all analyses for a user profile
        
        Args:
            user_profile_id: User profile ID
            
        Returns:
            List[FinancialAnalysis]: All analyses for the profile
        """
        async with self.__session as conn:
            result = await conn.execute(
                select(FinancialAnalysis)
                .where(FinancialAnalysis.user_profile_id == user_profile_id)
                .order_by(FinancialAnalysis.created_at.desc())
            )
            return list(result.scalars().all())

    async def create_bulk_analyses(self, analyses_data: List[tuple[FinancialAnalysisCreateDTO, int]]) -> List[FinancialAnalysis]:
        """Create multiple financial analyses in bulk
        
        Args:
            analyses_data: List of tuples containing (analysis_data, user_profile_id)
            
        Returns:
            List[FinancialAnalysis]: Created analyses
        """
        async with self.__session as conn:
            analyses = []
            for analysis_data, user_profile_id in analyses_data:
                analysis = FinancialAnalysis(
                    **analysis_data.model_dump(),
                    user_profile_id=user_profile_id
                )
                analyses.append(analysis)
                conn.add(analysis)
            
            await conn.commit()
            for analysis in analyses:
                await conn.refresh(analysis)
                conn.expunge(analysis)
            
            return analyses

    async def get_recent_analyses(self, limit: int = 50) -> List[FinancialAnalysis]:
        """Get recent analyses
        
        Args:
            limit: Maximum number of analyses to return
            
        Returns:
            List[FinancialAnalysis]: Recent analyses
        """
        async with self.__session as conn:
            result = await conn.execute(
                select(FinancialAnalysis)
                .order_by(FinancialAnalysis.created_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())

    async def get_analysis_stats(self) -> dict:
        """Get analysis statistics
        
        Returns:
            dict: Statistics about analyses
        """
        async with self.__session as conn:
            # Count by financial status
            from sqlalchemy import func
            
            result = await conn.execute(
                select(
                    FinancialAnalysis.financial_status,
                    func.count(FinancialAnalysis.id).label("count"),
                    func.avg(FinancialAnalysis.confidence_score).label("avg_confidence")
                )
                .group_by(FinancialAnalysis.financial_status)
            )
            
            stats = {}
            total_count = 0
            total_confidence = 0
            
            for row in result:
                stats[row.financial_status] = {
                    "count": row.count,
                    "average_confidence": float(row.avg_confidence) if row.avg_confidence else 0.0
                }
                total_count += row.count
                total_confidence += row.count * (row.avg_confidence or 0)
            
            stats["total"] = {
                "count": total_count,
                "average_confidence": total_confidence / total_count if total_count > 0 else 0.0
            }
            
            return stats