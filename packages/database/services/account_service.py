"Account service module"
import logging
from typing import List
import aiohttp
from sqlalchemy import select
from zendriver import Browser
from packages.database.database import Database
from packages.database.models import Account
from packages.sns_utils.browser import BrowserUtil
from sqlalchemy.orm import selectinload

class AccountService:
  """
    Service for managing Account entities.
  """

  def __init__(self):
    self.__session = Database.get_session()
    self.logger = logging.getLogger("AccountService")

  async def add_account(self, username, password, **kwargs) -> Account:
    """Add a new account.

    Args:
        username (str): The username for the account.
        password (str): The password for the account.
        **kwargs: Additional keyword arguments for the account.

    Returns:
        Account: The created Account object.
    """
    async with self.__session as conn:
      account = Account(username=username, password=password, **kwargs)
      conn.add(account)
      await conn.commit()
      await conn.refresh(account)
      conn.expunge(account)
      return account

  async def get_all_account(self) -> List[Account]:
    """Get all accounts.

    Returns:
        List[Account]: A list of all Account objects.
    """
    async with self.__session as conn:
      result = await conn.execute(select(Account))
      return list(result.scalars().all())

  async def get_ok_account(self) -> Account | None:
    """Get a working account.

    Returns:
        Account | None: The valid Account object or None if not found.
    """
    async with self.__session as conn:
      result = await conn.execute(
        select(Account)
        .where(Account.is_block.is_not(False),
          Account.access_token.is_not(None),
          Account.cookies.is_not(None)))
      return result.scalar_one_or_none()

  async def get_account_by_id(self, account_id: int) -> Account | None:
    """Get an account by its ID.

    Args:
        id (int): The ID of the account.

    Returns:
        Account | None: The Account object with the given ID or None if not found.
    """
    async with self.__session as conn:
      result = await conn.execute(
        select(Account).options(selectinload(Account.proxy)).where(Account.id == account_id)
      )
      return result.scalar_one_or_none()

  async def update_account(self, account: Account) -> None:
    """Update an existing account.

    Args:
        account (Account): The Account object to update.
    """
    async with self.__session as conn:
      conn.add(account)
      await conn.commit()
      await conn.refresh(account)
      conn.expunge(account)

  async def login_account(self, account: Account) -> bool:  # noqa: PLR6301
    """Log in with an account and save its cookies.

    Args:
        account (Account): The Account object to log in.

    Returns:
        bool: True if the login was successful, False otherwise.
    """
    try:
      browser: Browser = await BrowserUtil(
        proxy=account.proxy,
        user_data_dir=account.get_user_data_dir()
      ).get_browser()
      await browser.main_tab.get(f"https://www.facebook.com?username={account.username}&password={account.password}")
      while True:
        if len(browser.tabs) < 1:
          await self.update_account(account)
          break
        account.cookies = await browser.cookies.get_all() # type: ignore
        await browser.main_tab.sleep(1)
      return True
    except Exception as e:
      self.logger.error(f"Error logging in account {account.id}: {e}")
      return False

  async def gen_access_token(self, account: Account) -> str | None:
    """Generate the access token for a logged-in account.

    Args:
        account (Account): The Account object to get the access token for.

    Returns:
        str | None: The access token if found, None otherwise.
    """
    cookies = BrowserUtil.cookie_converter(account.cookies)
    async with aiohttp.ClientSession(cookies=cookies) as session:
      async with session.get("https://business.facebook.com/content_management") as resp:
        text = await resp.text(encoding="utf-8", errors="ignore")
        idx = text.find("EAAG")
        if idx == -1:
          self.logger.warning(f"Access token not found for account {account.id}")
          return None
        token = text[idx:text.find('"', idx)]
        account.access_token = token
        await self.update_account(account)
        return token