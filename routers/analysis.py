from fastapi import APIRouter, HTTPException

from packages.database.services.group_service import GroupService
from packages.database.services.post_service import PostService

router = APIRouter(
  prefix="/analysis",
	tags=["analysis"],
)

@router.post("/scan/group/{group_id}")
async def scan_group(group_id: str):
  try:
    group_service = GroupService()
    post_service = PostService()
    posts = await group_service.scan_group(
      group_id
    )
    success_count = await post_service.insert_posts(posts, ignore_errors=True)
    return {
      "status": "success",
      "added_post": success_count
    }
  except Exception as e:
    group_service.logger.exception(e)
    raise HTTPException(
      status_code=500,
      detail="Failed to scan group: " + str(e)
    )