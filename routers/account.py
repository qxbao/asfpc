from sqlalchemy import select
from fastapi import APIRouter
from packages.database.database import Database
from packages.database.models.account import Account, AccountSchema

router = APIRouter(
	prefix="/account",
	tags=["account"],
)

@router.get("/page/{page_number}")
async def get_all_accounts(page_number: int) -> list[AccountSchema]:
	LIMIT = 20
	async with Database.get_session() as session:
		accounts = (await session.execute(
				select(Account).offset((page_number - 1) * LIMIT).limit(LIMIT)
			)).scalars().all()
		return [account.to_schema() for account in accounts]

@router.get("/id/{account_id}")
async def get_account(account_id: int) -> AccountSchema | None:
	async with Database.get_session() as session:
		account = await session.get(Account, account_id)
		if account:
			return account.to_schema()
		return None