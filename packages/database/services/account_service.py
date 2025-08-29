from typing import List
from sqlalchemy import insert, select
from ..database import Database
from ..models.account import Account, AccountSchema

class AccountService:
  def __init__(self):
    self.__session = Database.get_session()

  async def add_account(self, username, password, **kwargs) -> Account:
    async with self.__session as conn:
      account = Account(username=username, password=password, **kwargs)
      conn.add(account)
      await conn.commit()
      await conn.refresh(account)
      conn.expunge(account)
      return account
    
  async def get_all_account(self) -> List[Account]:
    async with self.__session as conn:
      result = await conn.execute(select(Account))
      return result.scalars().all()
    
  async def get_ok_account(self) -> Account | None:
    async with self.__session as conn:
      result = await conn.execute(select(Account).where(Account.is_block.is_not(False), Account.access_token.is_not(None), Account.cookies.is_not(None)))
      return result.scalar_one_or_none()
    
  async def get_account_by_id(self, id: int) -> Account | None:
    async with self.__session as conn:
      result = await conn.execute(select(Account).where(Account.id == id))
      return result.scalar_one_or_none()

  async def update_account(self, account: Account) -> None:
    async with self.__session as conn:
      conn.add(account)
      await conn.commit()
      await conn.refresh(account)
      conn.expunge(account)

  async def login_account(self, account: Account) -> bool:
    return True