"""
用户偏好设置 API 路由
用于保存和获取用户级配置（如页面区块顺序、主题等）
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import logging
from datetime import datetime

from app.routers.auth_db import get_current_user
from app.core.database import get_mongo_db
from app.core.response import ok

logger = logging.getLogger("webapi")

router = APIRouter(prefix="/user", tags=["用户偏好设置"])


class UserSettingsRequest(BaseModel):
    """保存用户设置请求"""
    settings: Dict[str, Any]


@router.get("/settings", response_model=dict)
async def get_user_settings(
    current_user: dict = Depends(get_current_user)
):
    """
    获取当前用户的偏好设置
    """
    try:
        db = get_mongo_db()
        collection = db.user_settings
        user_id = str(current_user.get("id", current_user.get("_id", "")))

        doc = await collection.find_one({"user_id": user_id})
        if doc:
            # 移除 MongoDB 内部字段
            settings = {k: v for k, v in doc.items() if not k.startswith("_")}
            settings.pop("user_id", None)
            settings.pop("updated_at", None)
            return ok(data=settings, message="获取用户设置成功")
        else:
            return ok(data={}, message="用户暂无自定义设置")
    except Exception as e:
        logger.error(f"获取用户设置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取用户设置失败: {str(e)}")


@router.post("/settings", response_model=dict)
async def save_user_settings(
    request: UserSettingsRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    保存当前用户的偏好设置（增量更新，不覆盖其他字段）
    """
    try:
        db = get_mongo_db()
        collection = db.user_settings
        user_id = str(current_user.get("id", current_user.get("_id", "")))

        if not user_id:
            raise HTTPException(status_code=401, detail="无法获取用户ID")

        # 构造更新文档
        update_doc = {
            "updated_at": datetime.utcnow()
        }
        # 合并传入的设置
        for key, value in request.settings.items():
            update_doc[key] = value

        result = await collection.update_one(
            {"user_id": user_id},
            {"$set": update_doc},
            upsert=True
        )

        action = "新建" if result.upserted_id else "更新"
        logger.info(f"✅ {action}用户设置: user_id={user_id}, keys={list(request.settings.keys())}")

        return ok(data={"success": True}, message="用户设置已保存")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存用户设置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"保存用户设置失败: {str(e)}")


@router.get("/settings/{key}", response_model=dict)
async def get_user_setting_by_key(
    key: str,
    current_user: dict = Depends(get_current_user)
):
    """
    获取当前用户指定 key 的设置值
    """
    try:
        db = get_mongo_db()
        collection = db.user_settings
        user_id = str(current_user.get("id", current_user.get("_id", "")))

        doc = await collection.find_one({"user_id": user_id}, {key: 1})
        if doc and key in doc:
            return ok(data={"value": doc[key]}, message="获取设置项成功")
        else:
            return ok(data={"value": None}, message="该设置项不存在")
    except Exception as e:
        logger.error(f"获取用户设置项失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取用户设置项失败: {str(e)}")
