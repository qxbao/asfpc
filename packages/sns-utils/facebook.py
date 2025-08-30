"""Facebook profile scraping service"""
import asyncio
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from datetime import datetime
import sys
import os

# Add the project root to the path to enable imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import zendriver
from packages.database.services.user_profile_service import UserProfileService
from packages.database.services.account_service import AccountService
from packages.database.models.user_profile import UserProfileCreateDTO
from packages.database.models.account import Account
import importlib.util

# Import BrowserUtil from the same directory
spec = importlib.util.spec_from_file_location("browser", os.path.join(os.path.dirname(__file__), "browser.py"))
browser_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(browser_module)
BrowserUtil = browser_module.BrowserUtil


class Facebook:
    """Facebook profile scraping service"""
    
    def __init__(self, browser_util: Optional[BrowserUtil] = None):
        self.browser_util = browser_util or BrowserUtil()
        self.user_profile_service = UserProfileService()
        self.account_service = AccountService()
        self.logger = logging.getLogger("Facebook")
        
    async def scrape_profile(self, profile_url: str, account: Account, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Scrape a Facebook profile
        
        Args:
            profile_url: URL of the Facebook profile to scrape
            account: Account to use for scraping
            force_refresh: Force re-scraping even if profile exists in cache
            
        Returns:
            Optional[Dict[str, Any]]: Scraped profile data or None if failed
        """
        try:
            # Extract Facebook ID from URL
            facebook_id = self._extract_facebook_id(profile_url)
            if not facebook_id:
                self.logger.error(f"Could not extract Facebook ID from URL: {profile_url}")
                return None
                
            # Check if profile needs scraping
            if not force_refresh:
                is_stale = await self.user_profile_service.is_profile_stale(facebook_id)
                if not is_stale:
                    self.logger.info(f"Profile {facebook_id} is fresh, skipping scrape")
                    existing_profile = await self.user_profile_service.get_profile_by_facebook_id(facebook_id)
                    return existing_profile.to_json() if existing_profile else None
            
            # Start browser and scrape
            browser = await self.browser_util.get_browser()
            try:
                # Load cookies and access token if available
                await self._setup_browser_session(browser, account)
                
                # Navigate to profile
                tab = browser.main_tab
                await tab.get(profile_url)
                await asyncio.sleep(3)  # Wait for page to load
                
                # Check if we're blocked or need login
                if await self._check_access_blocked(tab):
                    self.logger.warning(f"Access blocked for profile {profile_url}")
                    return None
                
                # Scrape profile data
                profile_data = await self._scrape_profile_data(tab, facebook_id, profile_url)
                if not profile_data:
                    return None
                
                # Save to database
                profile_dto = UserProfileCreateDTO(**profile_data)
                saved_profile = await self.user_profile_service.create_profile(
                    profile_dto,
                    account.id
                )
                
                self.logger.info(f"Successfully scraped profile {facebook_id}")
                return saved_profile.to_json()
                
            finally:
                await browser.close()
                
        except Exception as e:
            self.logger.error(f"Error scraping profile {profile_url}: {str(e)}")
            return None
    
    async def batch_scrape_profiles(self, profile_urls: list[str], account: Account,
                                   delay_seconds: int = 5) -> list[Dict[str, Any]]:
        """Scrape multiple profiles with rate limiting
        
        Args:
            profile_urls: List of profile URLs to scrape
            account: Account to use for scraping
            delay_seconds: Delay between scrapes to avoid rate limiting
            
        Returns:
            list[Dict[str, Any]]: List of scraped profile data
        """
        results = []
        
        for i, url in enumerate(profile_urls):
            self.logger.info(f"Scraping profile {i+1}/{len(profile_urls)}: {url}")
            
            profile_data = await self.scrape_profile(url, account)
            if profile_data:
                results.append(profile_data)
            else:
                self.logger.warning(f"Failed to scrape profile: {url}")
            
            # Rate limiting
            if i < len(profile_urls) - 1:  # Don't delay after last profile
                await asyncio.sleep(delay_seconds)
        
        return results
    
    def _extract_facebook_id(self, profile_url: str) -> Optional[str]:
        """Extract Facebook user ID from profile URL"""
        try:
            parsed = urlparse(profile_url)
            
            # Handle different Facebook URL formats
            if "facebook.com" not in parsed.netloc:
                return None
                
            path = parsed.path.strip("/")
            
            # Handle facebook.com/profile.php?id=123456789
            if path == "profile.php":
                from urllib.parse import parse_qs
                query_params = parse_qs(parsed.query)
                if "id" in query_params:
                    return query_params["id"][0]
            
            # Handle facebook.com/username format
            if path and not path.startswith("profile.php"):
                # Remove any additional path segments
                username = path.split("/")[0]
                return username
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting Facebook ID from {profile_url}: {str(e)}")
            return None
    
    async def _setup_browser_session(self, browser: zendriver.Browser, account: Account):
        """Setup browser session with account cookies and tokens"""
        tab = browser.main_tab
        
        # Navigate to Facebook first
        await tab.get("https://facebook.com")
        
        # Set cookies if available
        if account.cookies:
            try:
                # Convert cookies to the format zendriver expects
                for cookie in account.cookies:
                    await tab.set_cookie(
                        name=cookie.name,
                        value=cookie.value,
                        domain=cookie.domain or ".facebook.com",
                        path=cookie.path or "/",
                        secure=cookie.secure or False,
                        httponly=cookie.httponly or False
                    )
                self.logger.info(f"Set {len(account.cookies)} cookies for account {account.username}")
            except Exception as e:
                self.logger.warning(f"Failed to set cookies: {str(e)}")
        
        # Refresh page after setting cookies
        await tab.get("https://facebook.com")
        await asyncio.sleep(2)
    
    async def _check_access_blocked(self, tab: zendriver.Tab) -> bool:
        """Check if access is blocked or login is required"""
        try:
            # Check for login page indicators
            page_source = await tab.get_content()
            
            blocked_indicators = [
                "login",
                "Sign Up",
                "Create New Account",
                "blocked",
                "not available",
                "This content isn't available",
                "You must log in"
            ]
            
            for indicator in blocked_indicators:
                if indicator.lower() in page_source.lower():
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking access: {str(e)}")
            return True
    
    async def _scrape_profile_data(self, tab: zendriver.Tab, facebook_id: str,
                                  profile_url: str) -> Optional[Dict[str, Any]]:
        """Scrape profile data from the loaded page"""
        try:
            profile_data = {
                "facebook_id": facebook_id,
                "profile_url": profile_url,
                "is_verified": False,
                "last_scraped": datetime.now()
            }
            
            # Get page content
            await asyncio.sleep(2)  # Allow page to fully load
            
            # Scrape name
            try:
                name_element = await tab.find_element("h1")
                if name_element:
                    profile_data["name"] = await name_element.get_text()
            except:
                pass
            
            # Scrape bio/about section
            try:
                bio_selectors = [
                    '[data-overviewsection="about"]',
                    '[data-section="about"]',
                    ".about",
                    ".bio"
                ]
                
                for selector in bio_selectors:
                    try:
                        bio_element = await tab.find_element(selector)
                        if bio_element:
                            profile_data["bio"] = await bio_element.get_text()
                            break
                    except:
                        continue
            except:
                pass
            
            # Try to get work/education info
            try:
                work_selectors = [
                    '[data-overviewsection="work"]',
                    ".work_experience",
                    ".work"
                ]
                
                for selector in work_selectors:
                    try:
                        work_element = await tab.find_element(selector)
                        if work_element:
                            profile_data["work"] = await work_element.get_text()
                            break
                    except:
                        continue
            except:
                pass
            
            # Try to get education info
            try:
                edu_selectors = [
                    '[data-overviewsection="education"]',
                    ".education",
                    ".school"
                ]
                
                for selector in edu_selectors:
                    try:
                        edu_element = await tab.find_element(selector)
                        if edu_element:
                            profile_data["education"] = await edu_element.get_text()
                            break
                    except:
                        continue
            except:
                pass
            
            # Try to get location
            try:
                location_selectors = [
                    '[data-overviewsection="places"]',
                    ".location",
                    ".hometown"
                ]
                
                for selector in location_selectors:
                    try:
                        location_element = await tab.find_element(selector)
                        if location_element:
                            profile_data["location"] = await location_element.get_text()
                            break
                    except:
                        continue
            except:
                pass
            
            # Try to get profile picture
            try:
                img_element = await tab.find_element('img[data-imgperflogname="profileCoverPhoto"]')
                if not img_element:
                    img_element = await tab.find_element(".profilePicThumb img")
                if img_element:
                    profile_data["profile_picture_url"] = await img_element.get_attribute("src")
            except:
                pass
            
            # Sample recent posts (if accessible)
            try:
                post_elements = await tab.find_elements('[data-testid="story-subtilte"]')
                if post_elements:
                    posts = []
                    for element in post_elements[:5]:  # Get up to 5 recent posts
                        post_text = await element.get_text()
                        if post_text and len(post_text.strip()) > 10:  # Ignore very short posts
                            posts.append(post_text.strip())
                    
                    if posts:
                        profile_data["posts_sample"] = "\n---\n".join(posts)
            except:
                pass
            
            # Check if profile has any meaningful data
            has_data = any([
                profile_data.get("name"),
                profile_data.get("bio"),
                profile_data.get("work"),
                profile_data.get("education"),
                profile_data.get("location")
            ])
            
            if not has_data:
                self.logger.warning(f"No meaningful data found for profile {facebook_id}")
                return None
            
            self.logger.info(f"Scraped profile data for {facebook_id}: {list(profile_data.keys())}")
            return profile_data
            
        except Exception as e:
            self.logger.error(f"Error scraping profile data: {str(e)}")
            return None