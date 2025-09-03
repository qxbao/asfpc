"""Router for /user path"""
import logging
from sqlalchemy import select
from fastapi import APIRouter, HTTPException
from packages.database.database import Database
from packages.database.models.account import Account, AccountSchema, AddAccountDTO
from packages.database.models.group import JoinGroupDTO, LinkGroupDTO
from packages.database.services.group_service import GroupService
from packages.database.services.account_service import AccountService

router = APIRouter(
	prefix="/account",
	tags=["Account endpoints"],
)

logger = logging.getLogger("AccountRouter")

@router.get("/page/{page_number}")
async def get_all_accounts(page_number: int) -> list[AccountSchema]:
	"""Get all accounts with pagination.

	Args:
			page_number (int): The page number to retrieve.

	Returns:
			list[AccountSchema]: A list of AccountSchema objects.
	"""
	limit = 20
	async with Database.get_session() as session:
		accounts = (await session.execute(
				select(Account).offset((page_number - 1) * limit).limit(limit)
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
		raise HTTPException(
			status_code=500,
			detail="Fail to add account: " + str(e)
		)

@router.post("/login/{account_id}")
async def login_account(account_id: int) -> dict:
	account_service = AccountService()
	try:
		account = await account_service.get_account_by_id(
			account_id=account_id
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
		logger.exception(e)
		raise HTTPException(
			status_code=500,
			detail="Fail to login account: " + str(e)
		)

@router.post("/gen_at/{account_id}")
async def gen_access_token(account_id: int) -> dict:
	account_service = AccountService()
	try:
		account = await account_service.get_account_by_id(
			account_id=account_id
		)
		if account is None:
			return {
				"error": "Account not found"
			}
		token = await account_service.gen_access_token(account)
		return {
			"status": "success" if token else "failed",
			"access_token": token
		}
	except Exception as e:
		logger.exception(e)
		raise HTTPException(
			status_code=500,
			detail="Fail to generate access token: " + str(e)
		)

@router.post("/group/link")
async def link_group(body: LinkGroupDTO) -> dict:
	account_service = AccountService()
	group_service = GroupService()
 
	try:
		account = await account_service.get_account_by_id(
			account_id=body.account_id
		)
		if account is None:
			return {
				"error": "Account not found"
			}
		linked_group = await group_service.link_group(account,
			body.group_id,
			body.group_name,
			body.is_joined
		)
		return {
			"status": "success",
			"details": linked_group.to_schema()
		}
	except Exception as e:
		logger.exception(e)
		raise HTTPException(
			status_code=500,
			detail="Fail to link group: " + str(e)
   	)
  
@router.post("/group/join")
async def join_group(body: JoinGroupDTO):
	try:
		account_service = AccountService()
		group_service = GroupService()
		account = await account_service.get_account_by_id(body.account_id)
		group = await group_service.get_group_by_id(body.group_id)
		if not account or not group:
			raise HTTPException(status_code=404, detail="Account or group not found")
		res = await account_service.join_group(account, group)
		if res:
			group.is_joined = True
			await group_service.update_group(
				group
			)
		return {
			"status": res
		}
	except Exception as e:
		logger.exception(e)
		raise HTTPException(
			status_code=500,
			detail="Fail to join group: " + str(e)
	 	)