from typing import Optional
import zendriver
import os
import logging

class BrowserUtil:
  proxy_url: Optional[str]
  user_data_dir: Optional[os.PathLike]
  logger = logging.get_logger("BrowserUtil")
  
  def __init__(self, proxy_url: Optional[str] = None, user_data_dir: Optional[os.PathLike] = None):
    self.proxy_url = proxy_url
    self.user_data_dir = user_data_dir

  async def get_browser(self, browser_args: list[str] = [], **kwargs) -> zendriver.Browser:
    browser = await zendriver.Browser.create(
      headless=False,
      user_data_dir=self.user_data_dir,
      args=browser_args,
      **kwargs
    )
    if self.proxy_url:
      await self.__config_proxy(browser)
    return browser
  
  async def __config_proxy(self, browser: zendriver.Browser, username: str, password: str):
    tab = browser.main_tab
    self.logger.info(f"username={username}")

    def req_paused(event: zendriver.cdp.fetch.RequestPaused):
        try:
            tab.feed_cdp(
                zendriver.cdp.fetch.continue_request(event.request_id, url=event.request.url)
            )
        except Exception as e:
            self.logger.warning(f"Failed to continue request {event.request_id}: {e}")

    def auth_challenge_handler(event: zendriver.cdp.fetch.AuthRequired):
        self.logger.info(f"auth_challenge_handler: {username}")
        tab.feed_cdp(
            zendriver.cdp.fetch.continue_with_auth(
                request_id=event.request_id,
                auth_challenge_response=zendriver.cdp.fetch.AuthChallengeResponse(
                    response="ProvideCredentials",
                    username=username,
                    password=password,
                ),
            )
        )

    tab.add_handler(zendriver.cdp.fetch.RequestPaused, req_paused)
    tab.add_handler(zendriver.cdp.fetch.AuthRequired, auth_challenge_handler)
    await tab.send(zendriver.cdp.fetch.enable(handle_auth_requests=True))