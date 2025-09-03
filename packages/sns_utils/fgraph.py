import json
import logging
import os
import hashlib
import random
from typing import Optional
from fastapi import HTTPException
import requests
from urllib.parse import urlencode

from packages.database.models.comment import GraphCommentResponse
from packages.database.models.group import GraphPostResponse, Group
from packages.database.models.post import Post


class FacebookGraph:
  URL = {
    "BASE":"https://api.facebook.com/restserver.php",
    "GRAPH":"https://graph.facebook.com/v23.0"
  }
  API_SECRET="62f8ce9f74b12f84c123cc23437a4a32"
  API_KEY="882a8490361da98702bf97a021ddc14d"
  logger = logging.getLogger("FacebookGraph")
  def __init__(self):
    self.APP_ID = os.getenv("FB_APP_ID")
    self.APP_SECRET = os.getenv("FB_APP_SECRET")
    self.access_token = None

  @staticmethod
  def __get_random_user_agent() -> str:
    """Get a random mobile user agent"""
    user_agents = [
      ("Mozilla/5.0 (Linux; Android 5.0.2; Andromax C46B2G Build/LRX22G) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Version/4.0 Chrome/37.0.0.0 Mobile Safari/537.36 "
       "[FB_IAB/FB4A;FBAV/60.0.0.16.76;]"),
      ("[FBAN/FB4A;FBAV/35.0.0.48.273;FBDM/{density=1.33125,width=800,height=1205};"
       "FBLC/en_US;FBCR/;FBPN/com.facebook.katana;FBDV/Nexus 7;FBSV/4.1.1;FBBK/0;]"),
      ("Mozilla/5.0 (Linux; Android 5.1.1; SM-N9208 Build/LMY47X) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/51.0.2704.81 Mobile Safari/537.36"),
      ("Mozilla/5.0 (Linux; U; Android 5.0; en-US; ASUS_Z008 Build/LRX21V) "
       "AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 UCBrowser/10.8.0.718 "
       "U3/0.8.0 Mobile Safari/534.30"),
      ("Mozilla/5.0 (Linux; U; Android 5.1; en-US; E5563 Build/29.1.B.0.101) "
       "AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 UCBrowser/10.10.0.796 "
       "U3/0.8.0 Mobile Safari/534.30"),
      ("Mozilla/5.0 (Linux; U; Android 4.4.2; en-us; Celkon A406 Build/MocorDroid2.3.5) "
       "AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1")
    ]
    return random.choice(user_agents)

  def __sign_creator(self, data: dict) -> dict:
    """Create signature for Facebook API request"""
    sig = ""
    for key, value in data.items():
      sig += f"{key}={value}"
    sig += self.API_SECRET
    sig = hashlib.md5(sig.encode()).hexdigest()
    data["sig"] = sig
    return data

  def get_access_token(self, email: str, password: str) -> str | None:
    """Get access token using email and password via Facebook REST API"""
    try:
      data = {
        "api_key": self.API_KEY,
        "credentials_type": "password",
        "email": email,
        "format": "JSON",
        "generate_machine_id": "1",
        "generate_session_cookies": "1",
        "locale": "en_US",
        "method": "auth.login",
        "password": password,
        "return_ssl_resources": "0",
        "v": "1.0"
      }

      data = self.__sign_creator(data)
      url = f"{self.URL.get('BASE', 'https://api.facebook.com/restserver.php')}?{urlencode(data)}"
      headers = {
        "User-Agent": FacebookGraph.__get_random_user_agent()
      }
      response = requests.get(url, headers=headers)
      response_data = response.json()
      
      if "access_token" in response_data:
        self.access_token = response_data["access_token"]
        return self.access_token
      else:
        return None

    except Exception as e:
      self.logger.exception(e)
      raise e

  def query(self, path: str,
      headers: Optional[dict] = None,
      access_token: Optional[str] = None,
      **kwargs) -> dict:
    if not access_token:
      access_token = self.access_token
    try:
      params = "&".join([f"{key}={value}" for key, value in kwargs.items()]) \
                + f"&access_token={access_token}"
      url = f"{self.URL.get('GRAPH', 'https://graph.facebook.com/v23.0')}/{path}?{params}"
      self.logger.info(f"Send GET Request to URL: {url}")
      response = requests.get(url, headers=headers)
      data = response.json()
      return data
    except Exception as e:
      self.logger.exception(e)
      raise HTTPException(status_code=500, detail=str(e))

  def get_posts_from_group(
    self,
    group: Group,
    **kwargs,
  ) -> GraphPostResponse:
    """Get posts for a specific group."""
    return GraphPostResponse.model_validate_json(
      json.dumps(
        self.query(
          f"{group.group_id}/feed",
          **kwargs
        )
      )
    )

  def get_posts_comments(
    self,
    Post: Post,
    **kwargs
  ) -> GraphCommentResponse:
    """Get comments for a specific post."""
    return GraphCommentResponse.model_validate_json(
      json.dumps(
        self.query(
          f"{Post.post_id}/comments",
          **kwargs
        )
      )
    )