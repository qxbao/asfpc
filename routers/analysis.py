import logging
from fastapi import APIRouter, HTTPException

from packages.database.services.comment_service import CommentService
from packages.database.services.group_service import GroupService
from packages.database.services.post_service import PostService

router = APIRouter(
  prefix="/analysis",
	tags=["Analysis endpoints"],
)

logger = logging.getLogger("analysis")

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
    logger.exception(e)
    raise HTTPException(
      status_code=500,
      detail="Failed to scan group: " + str(e)
    )
    
@router.post("/scan/post/{post_id}")
async def scan_post(post_id: str):
  try:
    post_service = PostService()
    comment_service = CommentService()
    comments = await post_service.scan_post(post_id)
    success_count = await comment_service.insert_comments(comments, ignore_errors=True)
    return {
      "status": "success",
      "added_comment": success_count
    }
  except Exception as e:
    logger.exception(e)
    raise HTTPException(
      status_code=500,
      detail="Failed to scan post: " + str(e)
    )