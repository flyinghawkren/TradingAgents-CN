"""
基础信息同步管理路由
提供手动触发基础信息同步、查询同步状态等功能
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from app.routers.auth_db import get_current_user
from app.services.basics_info_sync_service import get_basics_info_sync_service
from app.core.response import ok

router = APIRouter(prefix="/api/basics", tags=["基础信息同步"])


@router.post("/sync", response_model=dict)
async def trigger_basics_sync(
    current_user: dict = Depends(get_current_user)
):
    """
    手动触发基础信息同步（股票 + 基金）

    如果同步正在执行中，将返回错误提示，避免重复触发
    """
    service = get_basics_info_sync_service()

    if service.is_running:
        return ok(data={
            "success": False,
            "already_running": True,
            "message": "基础信息同步正在执行中，请稍后再试"
        }, message="同步正在执行中")

    try:
        # 异步启动同步（不等待完成）
        import asyncio
        asyncio.create_task(service.sync_all())

        return ok(data={
            "success": True,
            "already_running": False,
            "message": "基础信息同步已启动，请在任务中心查看进度"
        }, message="同步已启动")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动同步失败: {str(e)}")


@router.get("/status", response_model=dict)
async def get_basics_sync_status(
    current_user: dict = Depends(get_current_user)
):
    """
    获取基础信息同步状态

    返回：
    - is_running: 是否正在同步
    - last_sync_time: 上次同步时间
    - last_result: 上次同步结果
    - stock_count: 本地股票基础信息数量
    - fund_count: 本地基金基础信息数量
    """
    service = get_basics_info_sync_service()
    stats = await service.get_stats()
    return ok(data=stats, message="获取同步状态成功")


@router.get("/stocks", response_model=dict)
async def search_stock_basics(
    keyword: str = "",
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """
    搜索股票基础信息（用于搜索补全）
    """
    service = get_basics_info_sync_service()
    results = await service.get_stock_basics(keyword=keyword, limit=limit)
    return ok(data=results, message=f"找到 {len(results)} 条股票记录")


@router.get("/funds", response_model=dict)
async def search_fund_basics(
    keyword: str = "",
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """
    搜索基金基础信息（用于搜索补全）
    """
    service = get_basics_info_sync_service()
    results = await service.get_fund_basics(keyword=keyword, limit=limit)
    return ok(data=results, message=f"找到 {len(results)} 条基金记录")
