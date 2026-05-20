"""
智能投资 Agent API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import logging

from app.routers.auth_db import get_current_user
from app.core.response import ok
from app.services.agent.agent_service import get_agent_service

logger = logging.getLogger("webapi")
router = APIRouter(prefix="/agent", tags=["智能投资"])


class ChatRequest(BaseModel):
    message: str


@router.post("/chat", response_model=dict)
async def agent_chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """智能投资对话"""
    try:
        agent = get_agent_service()
        result = await agent.chat(request.message, current_user["id"])
        return ok(data=result, message="处理成功")
    except Exception as e:
        logger.error(f"Agent 对话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"对话处理失败: {str(e)}")
