"""Router for profile analysis endpoints"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import List, Optional
from pydantic import BaseModel, Field
import importlib.util
import os

from packages.database.services.user_profile_service import UserProfileService
from packages.database.services.financial_analysis_service import FinancialAnalysisService
from packages.database.services.account_service import AccountService
from packages.database.models.user_profile import UserProfileSchema
from packages.database.models.financial_analysis import (
    FinancialAnalysisSchema,
    BatchAnalysisRequest,
    BatchAnalysisResponse
)

# Import modules from sns-utils directory
def import_from_sns_utils(module_name):
    """Import a module from the sns-utils directory"""
    module_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "packages", "sns-utils", f"{module_name}.py")
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

facebook_module = import_from_sns_utils("facebook")
gemini_module = import_from_sns_utils("gemini_service")

Facebook = facebook_module.Facebook
GeminiAnalysisService = gemini_module.GeminiAnalysisService

router = APIRouter(
    prefix="/analysis",
    tags=["analysis"],
)

# Request/Response models
class ScrapeProfileRequest(BaseModel):
    """Request to scrape a Facebook profile"""
    profile_url: str = Field(..., description="Facebook profile URL")
    account_id: int = Field(..., description="Account ID to use for scraping")
    force_refresh: bool = Field(default=False, description="Force re-scraping even if profile exists")

class BulkScrapeRequest(BaseModel):
    """Request to scrape multiple Facebook profiles"""
    profile_urls: List[str] = Field(..., min_length=1, max_length=20, description="List of Facebook profile URLs")
    account_id: int = Field(..., description="Account ID to use for scraping")
    delay_seconds: int = Field(default=5, ge=1, le=30, description="Delay between scrapes")

class AnalyzeProfileRequest(BaseModel):
    """Request to analyze a profile"""
    profile_id: int = Field(..., description="Profile ID to analyze")
    force_reanalysis: bool = Field(default=False, description="Force re-analysis even if recent analysis exists")

# Helper function to get services (initialized when needed)
def get_services():
    """Get service instances"""
    return {
        "user_profile_service": UserProfileService(),
        "financial_analysis_service": FinancialAnalysisService(),
        "account_service": AccountService()
    }

@router.post("/scrape-profile")
async def scrape_profile(request: ScrapeProfileRequest) -> dict:
    """Scrape a single Facebook profile
    
    This endpoint scrapes a Facebook profile and stores the data in the database.
    It uses the provided account for authentication and respects caching.
    """
    try:
        services = get_services()
        account_service = services["account_service"]
        
        # Validate account
        account = await account_service.get_account_by_id(request.account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        if account.is_block:
            raise HTTPException(status_code=400, detail="Account is blocked")
        
        # Initialize Facebook scraper
        facebook = Facebook()
        
        # Scrape profile
        result = await facebook.scrape_profile(
            request.profile_url,
            account,
            request.force_refresh
        )
        
        if not result:
            raise HTTPException(status_code=400, detail="Failed to scrape profile")
        
        return {
            "success": True,
            "message": "Profile scraped successfully",
            "profile": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/scrape-profiles/bulk")
async def scrape_profiles_bulk(request: BulkScrapeRequest, background_tasks: BackgroundTasks) -> dict:
    """Scrape multiple Facebook profiles in bulk
    
    This endpoint scrapes multiple Facebook profiles with rate limiting.
    Processing happens in the background to avoid timeout issues.
    """
    try:
        services = get_services()
        account_service = services["account_service"]
        
        # Validate account
        account = await account_service.get_account_by_id(request.account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        if account.is_block:
            raise HTTPException(status_code=400, detail="Account is blocked")
        
        # Start bulk scraping in background
        background_tasks.add_task(
            _background_bulk_scrape,
            request.profile_urls,
            account,
            request.delay_seconds
        )
        
        return {
            "success": True,
            "message": f"Started bulk scraping of {len(request.profile_urls)} profiles",
            "estimated_completion_minutes": len(request.profile_urls) * request.delay_seconds / 60
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/analyze-profile")
async def analyze_profile(request: AnalyzeProfileRequest) -> dict:
    """Analyze a single profile for financial status
    
    This endpoint uses Google Gemini AI to analyze a profile's financial status
    based on the scraped profile data.
    """
    try:
        services = get_services()
        user_profile_service = services["user_profile_service"]
        
        # Get profile
        profile = await user_profile_service.get_profile_by_id(request.profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Initialize Gemini service
        gemini_service = GeminiAnalysisService()
        
        # Analyze profile
        result = await gemini_service.analyze_profile(profile, request.force_reanalysis)
        
        if not result:
            raise HTTPException(status_code=400, detail="Failed to analyze profile")
        
        return {
            "success": True,
            "message": "Profile analyzed successfully",
            "analysis": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/analyze-profiles/batch", response_model=BatchAnalysisResponse)
async def analyze_profiles_batch(request: BatchAnalysisRequest) -> BatchAnalysisResponse:
    """Analyze multiple profiles in batch for financial status
    
    This endpoint analyzes multiple profiles in batches to optimize token usage
    and provide efficient bulk analysis.
    """
    try:
        # Initialize Gemini service
        gemini_service = GeminiAnalysisService()
        
        # Perform batch analysis
        result = await gemini_service.batch_analyze_profiles(
            request.profile_ids,
            request.force_reanalysis
        )
        
        return BatchAnalysisResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/profiles")
async def get_profiles(
    limit: int = Query(default=50, ge=1, le=200),
    account_id: Optional[int] = Query(default=None)
) -> List[UserProfileSchema]:
    """Get recent profiles
    
    Returns a list of recently scraped profiles, optionally filtered by account.
    """
    try:
        services = get_services()
        user_profile_service = services["user_profile_service"]
        
        profiles = await user_profile_service.get_recent_profiles(account_id, limit)
        return [profile.to_schema() for profile in profiles]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/profiles/{profile_id}")
async def get_profile(profile_id: int) -> UserProfileSchema:
    """Get a specific profile by ID
    
    Returns detailed information about a specific profile including any analyses.
    """
    try:
        services = get_services()
        user_profile_service = services["user_profile_service"]
        
        profile = await user_profile_service.get_profile_by_id(profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        return profile.to_schema()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/profiles/{profile_id}/analyses")
async def get_profile_analyses(profile_id: int) -> List[FinancialAnalysisSchema]:
    """Get all analyses for a specific profile
    
    Returns all financial analyses performed on the specified profile.
    """
    try:
        services = get_services()
        user_profile_service = services["user_profile_service"]
        financial_analysis_service = services["financial_analysis_service"]
        
        # Verify profile exists
        profile = await user_profile_service.get_profile_by_id(profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        analyses = await financial_analysis_service.get_analyses_for_profile(profile_id)
        return [analysis.to_schema() for analysis in analyses]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/analyses/recent")
async def get_recent_analyses(limit: int = Query(default=50, ge=1, le=200)) -> List[FinancialAnalysisSchema]:
    """Get recent analyses
    
    Returns a list of recent financial analyses across all profiles.
    """
    try:
        services = get_services()
        financial_analysis_service = services["financial_analysis_service"]
        
        analyses = await financial_analysis_service.get_recent_analyses(limit)
        return [analysis.to_schema() for analysis in analyses]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/analyses/stats")
async def get_analysis_stats() -> dict:
    """Get analysis statistics
    
    Returns statistics about financial analyses including distribution by status
    and average confidence scores.
    """
    try:
        services = get_services()
        financial_analysis_service = services["financial_analysis_service"]
        
        stats = await financial_analysis_service.get_analysis_stats()
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/profiles/needing-analysis")
async def get_profiles_needing_analysis(limit: int = Query(default=10, ge=1, le=50)) -> List[UserProfileSchema]:
    """Get profiles that need analysis
    
    Returns profiles that haven't been analyzed or need re-analysis.
    """
    try:
        services = get_services()
        user_profile_service = services["user_profile_service"]
        
        profiles = await user_profile_service.get_profiles_needing_analysis(limit)
        return [profile.to_schema() for profile in profiles]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Background task functions
async def _background_bulk_scrape(profile_urls: List[str], account, delay_seconds: int):
    """Background task for bulk profile scraping"""
    import logging
    logger = logging.getLogger("BulkScrape")
    
    try:
        facebook = Facebook()
        results = await facebook.batch_scrape_profiles(profile_urls, account, delay_seconds)
        
        logger.info(f"Bulk scraping completed. Successfully scraped {len(results)}/{len(profile_urls)} profiles")
        
    except Exception as e:
        logger.error(f"Error in bulk scraping: {str(e)}")