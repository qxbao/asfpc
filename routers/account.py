from sqlalchemy import select
from fastapi import APIRouter
from packages.database.database import Database
from packages.database.models import account
from packages.database.models.account import Account, AccountSchema, AddAccountDTO
from packages.database.services.account_service import AccountService

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

@router.post("/add")
async def add_account(account: AddAccountDTO) -> AccountSchema | None:
	account_service = AccountService()
	try:
		new_account = await account_service.add_account(
			username=account.username,
			email=account.email,
			password=account.password,
			is_block=False,
			proxy_id=None
		)
		return new_account.to_schema()
	except Exception as e:
		return {
			"error": "Fail to add account",
			"details": str(e)
		}
  
@router.post("/login/{account_id}")
async def login_account(account_id: int) -> dict:
	account_service = AccountService()
	try:
		account = await account_service.get_account_by_id(
			id=account_id
		)
		if account is None:
			return {
				"error": "Account not found"
			}
		is_login_ok = await account_service.login_account(account)
		return {
			"status": "success" if is_login_ok else "failed"
		}
	except Exception as e:
		return {
			"error": "Fail to login account",
			"details": str(e)
		}