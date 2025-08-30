"""Gemini AI service for financial analysis"""
import os
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import sys

# Add the project root to the path to enable imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

from packages.database.services.financial_analysis_service import FinancialAnalysisService
from packages.database.services.user_profile_service import UserProfileService
from packages.database.models.financial_analysis import FinancialAnalysisCreateDTO
from packages.database.models.user_profile import UserProfile


class GeminiAnalysisService:
    """Service for analyzing user profiles using Google Gemini AI"""
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self.logger = logging.getLogger("GeminiAnalysisService")
        
        self.financial_analysis_service = FinancialAnalysisService()
        self.user_profile_service = UserProfileService()
        
        if not GEMINI_AVAILABLE:
            self.logger.error("google-generative-ai package not installed. Run: pip install google-generative-ai")
            raise ImportError("google-generative-ai package required")
        
        if not self.api_key:
            self.logger.error("GEMINI_API_KEY environment variable not set")
            raise ValueError("GEMINI_API_KEY environment variable required")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)
        
        self.logger.info(f"Initialized GeminiAnalysisService with model {model_name}")
    
    async def analyze_profile(self, profile: UserProfile, force_reanalysis: bool = False) -> Optional[Dict[str, Any]]:
        """Analyze a single user profile for financial status
        
        Args:
            profile: UserProfile to analyze
            force_reanalysis: Force re-analysis even if recent analysis exists
            
        Returns:
            Optional[Dict[str, Any]]: Analysis results or None if failed
        """
        try:
            # Check if recent analysis exists
            if not force_reanalysis:
                existing_analysis = await self.financial_analysis_service.get_latest_analysis_for_profile(profile.id)
                if existing_analysis and self._is_analysis_recent(existing_analysis.created_at):
                    self.logger.info(f"Recent analysis exists for profile {profile.id}, skipping")
                    return existing_analysis.to_json()
            
            # Prepare profile data for analysis
            profile_text = self._prepare_profile_text(profile)
            if not profile_text.strip():
                self.logger.warning(f"No analyzable content for profile {profile.id}")
                return None
            
            # Generate analysis using Gemini
            analysis_result = await self._generate_analysis(profile_text)
            if not analysis_result:
                return None
            
            # Save analysis to database
            analysis_dto = FinancialAnalysisCreateDTO(
                financial_status=analysis_result["financial_status"],
                confidence_score=analysis_result["confidence_score"],
                analysis_summary=analysis_result["analysis_summary"],
                indicators=analysis_result.get("indicators"),
                gemini_model_used=self.model_name,
                prompt_tokens_used=analysis_result.get("prompt_tokens"),
                completion_tokens_used=analysis_result.get("completion_tokens"),
                total_tokens_used=analysis_result.get("total_tokens")
            )
            
            saved_analysis = await self.financial_analysis_service.create_analysis(
                analysis_dto,
                profile.id
            )
            
            self.logger.info(f"Successfully analyzed profile {profile.id} with status: {analysis_result['financial_status']}")
            return saved_analysis.to_json()
            
        except Exception as e:
            self.logger.error(f"Error analyzing profile {profile.id}: {str(e)}")
            return None
    
    async def batch_analyze_profiles(self, profile_ids: List[int],
                                   force_reanalysis: bool = False,
                                   batch_size: int = 5) -> Dict[str, Any]:
        """Analyze multiple profiles in batches to optimize token usage
        
        Args:
            profile_ids: List of profile IDs to analyze
            force_reanalysis: Force re-analysis even if recent analysis exists
            batch_size: Number of profiles to analyze in a single API call
            
        Returns:
            Dict[str, Any]: Batch analysis results
        """
        try:
            # Get profiles
            profiles = await self.user_profile_service.get_profiles_by_ids(profile_ids)
            if not profiles:
                return {"success": False, "error": "No profiles found", "results": []}
            
            # Filter profiles that need analysis
            if not force_reanalysis:
                profiles_to_analyze = []
                for profile in profiles:
                    existing_analysis = await self.financial_analysis_service.get_latest_analysis_for_profile(profile.id)
                    if not existing_analysis or not self._is_analysis_recent(existing_analysis.created_at):
                        profiles_to_analyze.append(profile)
                profiles = profiles_to_analyze
            
            if not profiles:
                return {"success": True, "results": [], "message": "All profiles have recent analysis"}
            
            # Process profiles in batches
            all_results = []
            errors = []
            total_tokens = 0
            
            for i in range(0, len(profiles), batch_size):
                batch = profiles[i:i + batch_size]
                self.logger.info(f"Processing batch {i//batch_size + 1}: {len(batch)} profiles")
                
                try:
                    batch_results = await self._analyze_batch(batch)
                    all_results.extend(batch_results["results"])
                    errors.extend(batch_results["errors"])
                    total_tokens += batch_results["total_tokens"]
                    
                    # Rate limiting - wait between batches
                    if i + batch_size < len(profiles):
                        await asyncio.sleep(2)
                        
                except Exception as e:
                    self.logger.error(f"Error processing batch {i//batch_size + 1}: {str(e)}")
                    errors.append({
                        "batch": i//batch_size + 1,
                        "error": str(e),
                        "profile_ids": [p.id for p in batch]
                    })
            
            return {
                "success": True,
                "results": all_results,
                "errors": errors,
                "total_tokens_used": total_tokens,
                "profiles_processed": len(all_results),
                "profiles_failed": len(errors)
            }
            
        except Exception as e:
            self.logger.error(f"Error in batch analysis: {str(e)}")
            return {"success": False, "error": str(e), "results": []}
    
    async def _analyze_batch(self, profiles: List[UserProfile]) -> Dict[str, Any]:
        """Analyze a batch of profiles in a single API call"""
        try:
            # Prepare batch prompt
            batch_prompt = self._prepare_batch_prompt(profiles)
            
            # Generate batch analysis
            response = await self._call_gemini_api(batch_prompt)
            
            # Parse batch response
            parsed_results = self._parse_batch_response(response, profiles)
            
            # Save analyses to database
            analyses_to_create = []
            results = []
            
            for result in parsed_results:
                if result["success"]:
                    analysis_dto = FinancialAnalysisCreateDTO(
                        financial_status=result["financial_status"],
                        confidence_score=result["confidence_score"],
                        analysis_summary=result["analysis_summary"],
                        indicators=result.get("indicators"),
                        gemini_model_used=self.model_name,
                        prompt_tokens_used=result.get("prompt_tokens"),
                        completion_tokens_used=result.get("completion_tokens"),
                        total_tokens_used=result.get("total_tokens")
                    )
                    analyses_to_create.append((analysis_dto, result["profile_id"]))
            
            # Bulk create analyses
            if analyses_to_create:
                saved_analyses = await self.financial_analysis_service.create_bulk_analyses(analyses_to_create)
                results.extend([analysis.to_json() for analysis in saved_analyses])
            
            return {
                "results": results,
                "errors": [r for r in parsed_results if not r["success"]],
                "total_tokens": sum(r.get("total_tokens", 0) for r in parsed_results)
            }
            
        except Exception as e:
            self.logger.error(f"Error in batch analysis: {str(e)}")
            return {
                "results": [],
                "errors": [{"error": str(e), "profile_ids": [p.id for p in profiles]}],
                "total_tokens": 0
            }
    
    def _prepare_profile_text(self, profile: UserProfile) -> str:
        """Prepare profile data for analysis"""
        text_parts = []
        
        if profile.name:
            text_parts.append(f"Name: {profile.name}")
        
        if profile.bio:
            text_parts.append(f"Bio: {profile.bio}")
        
        if profile.work:
            text_parts.append(f"Work: {profile.work}")
        
        if profile.education:
            text_parts.append(f"Education: {profile.education}")
        
        if profile.location:
            text_parts.append(f"Location: {profile.location}")
        
        if profile.posts_sample:
            text_parts.append(f"Recent Posts Sample: {profile.posts_sample}")
        
        return "\n".join(text_parts)
    
    def _prepare_batch_prompt(self, profiles: List[UserProfile]) -> str:
        """Prepare batch prompt for multiple profiles"""
        system_prompt = """
You are a financial analyst AI. Analyze the provided Facebook profiles to determine the user's likely financial status.

For each profile, provide analysis in this exact JSON format:
{
  "profile_id": <profile_id>,
  "financial_status": "low|medium|high",
  "confidence_score": <0.0-1.0>,
  "analysis_summary": "<brief explanation>",
  "indicators": {
    "job_indicators": ["list of job-related indicators found"],
    "lifestyle_indicators": ["list of lifestyle indicators found"],
    "education_indicators": ["list of education indicators found"],
    "location_indicators": ["list of location-based indicators found"]
  }
}

Financial Status Guidelines:
- LOW: Students, unemployed, entry-level jobs, financial struggles mentioned, budget constraints
- MEDIUM: Standard employment, middle-class lifestyle, some discretionary spending
- HIGH: Executive positions, luxury lifestyle indicators, high-end education, expensive locations/activities

Consider these factors:
1. Job titles and companies
2. Education level and institutions
3. Location (expensive areas indicate higher income)
4. Lifestyle posts (travel, dining, purchases, activities)
5. Language patterns indicating financial stress or success

Respond with a JSON array containing analysis for each profile.
"""
        
        profile_data = []
        for i, profile in enumerate(profiles):
            profile_text = self._prepare_profile_text(profile)
            profile_data.append(f"PROFILE {profile.id}:\n{profile_text}\n")
        
        full_prompt = system_prompt + "\n\nProfiles to analyze:\n" + "\n".join(profile_data)
        return full_prompt
    
    async def _generate_analysis(self, profile_text: str) -> Optional[Dict[str, Any]]:
        """Generate analysis for a single profile"""
        system_prompt = """
You are a financial analyst AI. Analyze this Facebook profile to determine the user's likely financial status.

Respond with valid JSON in this exact format:
{
  "financial_status": "low|medium|high",
  "confidence_score": <0.0-1.0>,
  "analysis_summary": "<brief explanation of your assessment>",
  "indicators": {
    "job_indicators": ["list of job-related indicators found"],
    "lifestyle_indicators": ["list of lifestyle indicators found"],
    "education_indicators": ["list of education indicators found"],
    "location_indicators": ["list of location-based indicators found"]
  }
}

Financial Status Guidelines:
- LOW: Students, unemployed, entry-level jobs, financial struggles mentioned, budget constraints
- MEDIUM: Standard employment, middle-class lifestyle, some discretionary spending  
- HIGH: Executive positions, luxury lifestyle indicators, high-end education, expensive locations/activities

Profile to analyze:
""" + profile_text
        
        try:
            response = await self._call_gemini_api(system_prompt)
            return self._parse_single_response(response)
        except Exception as e:
            self.logger.error(f"Error generating analysis: {str(e)}")
            return None
    
    async def _call_gemini_api(self, prompt: str) -> Any:
        """Call Gemini API with the given prompt"""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.model.generate_content(prompt)
            )
            return response
        except Exception as e:
            self.logger.error(f"Error calling Gemini API: {str(e)}")
            raise
    
    def _parse_single_response(self, response) -> Optional[Dict[str, Any]]:
        """Parse single profile analysis response"""
        try:
            import json
            
            # Get response text
            response_text = response.text.strip()
            
            # Clean up response text (remove markdown formatting if present)
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            # Parse JSON
            result = json.loads(response_text)
            
            # Validate required fields
            required_fields = ["financial_status", "confidence_score", "analysis_summary"]
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate financial_status
            if result["financial_status"] not in ["low", "medium", "high"]:
                raise ValueError(f"Invalid financial_status: {result['financial_status']}")
            
            # Validate confidence_score
            if not 0.0 <= result["confidence_score"] <= 1.0:
                raise ValueError(f"Invalid confidence_score: {result['confidence_score']}")
            
            # Add token usage info if available
            if hasattr(response, "usage_metadata"):
                result["prompt_tokens"] = getattr(response.usage_metadata, "prompt_token_count", None)
                result["completion_tokens"] = getattr(response.usage_metadata, "candidates_token_count", None)
                result["total_tokens"] = getattr(response.usage_metadata, "total_token_count", None)
            
            return result
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {str(e)}, Response: {response.text}")
            return None
        except Exception as e:
            self.logger.error(f"Error parsing response: {str(e)}")
            return None
    
    def _parse_batch_response(self, response, profiles: List[UserProfile]) -> List[Dict[str, Any]]:
        """Parse batch analysis response"""
        try:
            import json
            
            response_text = response.text.strip()
            
            # Clean up response text
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            # Parse JSON array
            results = json.loads(response_text)
            
            if not isinstance(results, list):
                raise ValueError("Expected JSON array response")
            
            # Validate and enhance results
            enhanced_results = []
            for result in results:
                try:
                    # Validate required fields
                    required_fields = ["profile_id", "financial_status", "confidence_score", "analysis_summary"]
                    for field in required_fields:
                        if field not in result:
                            raise ValueError(f"Missing required field: {field}")
                    
                    # Validate values
                    if result["financial_status"] not in ["low", "medium", "high"]:
                        raise ValueError(f"Invalid financial_status: {result['financial_status']}")
                    
                    if not 0.0 <= result["confidence_score"] <= 1.0:
                        raise ValueError(f"Invalid confidence_score: {result['confidence_score']}")
                    
                    # Add token usage info if available
                    if hasattr(response, "usage_metadata"):
                        result["prompt_tokens"] = getattr(response.usage_metadata, "prompt_token_count", None)
                        result["completion_tokens"] = getattr(response.usage_metadata, "candidates_token_count", None)
                        result["total_tokens"] = getattr(response.usage_metadata, "total_token_count", None)
                    
                    result["success"] = True
                    enhanced_results.append(result)
                    
                except Exception as e:
                    self.logger.error(f"Error validating result for profile {result.get('profile_id')}: {str(e)}")
                    enhanced_results.append({
                        "profile_id": result.get("profile_id"),
                        "success": False,
                        "error": str(e)
                    })
            
            return enhanced_results
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error in batch response: {str(e)}")
            return [{"success": False, "error": f"JSON decode error: {str(e)}", "profile_ids": [p.id for p in profiles]}]
        except Exception as e:
            self.logger.error(f"Error parsing batch response: {str(e)}")
            return [{"success": False, "error": str(e), "profile_ids": [p.id for p in profiles]}]
    
    def _is_analysis_recent(self, analysis_date: datetime, max_age_days: int = 7) -> bool:
        """Check if analysis is recent enough"""
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        return analysis_date > cutoff_date