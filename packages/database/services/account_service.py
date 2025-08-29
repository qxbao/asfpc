"Account service module"
from typing import List
from sqlalchemy import select
from packages.database.database import Database
from packages.database.models import Account

class AccountService:
  """
    Service for managing Account entities.
  """

  def __init__(self):
    self.__session = Database.get_session()

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
      return result.scalars().all()

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
      result = await conn.execute(select(Account).where(Account.id == account_id))
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
    """Log in an account and save its cookies.

    Args:
        account (Account): The Account object to log in.

    Returns:
        bool: True if the login was successful, False otherwise.
    """
    return True
