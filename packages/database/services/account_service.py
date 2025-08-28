from sqlalchemy import insert
from ..database import Database
from ..models.account import Account

class AccountService:
  def __init__(self):
    self.__session = Database.get_session()

  async def add_account(self, username, password, **kwargs):
    async with self.__session as conn:
      account = Account(username=username, password=password, **kwargs)
      conn.add(account)
      await conn.commit()
      return account