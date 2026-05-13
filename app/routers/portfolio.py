"""
投资组合管理API路由
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import logging

from app.routers.auth_db import get_current_user
from app.services.portfolio_service import portfolio_service
from app.core.response import ok

logger = logging.getLogger("webapi")

router = APIRouter(prefix="/portfolio", tags=["投资组合管理"])


class AddHoldingRequest(BaseModel):
    """添加持仓请求"""
    stock_code: str
    stock_name: str
    market: str = "A股"
    quantity: int
    avg_price: float
    buy_date: str
    notes: str = ""


class UpdateHoldingRequest(BaseModel):
    """更新持仓请求"""
    quantity: Optional[int] = None
    avg_price: Optional[float] = None
    buy_date: Optional[str] = None
    notes: Optional[str] = None


@router.get("/", response_model=dict)
async def get_holdings(
    current_user: dict = Depends(get_current_user)
):
    """获取用户持仓列表"""
    try:
        holdings = await portfolio_service.get_user_holdings(current_user["id"])
        return ok(holdings)
    except Exception as e:
        logger.error(f"获取持仓列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取持仓列表失败: {str(e)}"
        )


@router.post("/", response_model=dict)
async def add_holding(
    request: AddHoldingRequest,
    current_user: dict = Depends(get_current_user)
):
    """添加持仓记录"""
    try:
        logger.info(
            f"添加持仓: user_id={current_user['id']}, "
            f"stock_code={request.stock_code}, quantity={request.quantity}"
        )

        holding = await portfolio_service.add_holding(
            user_id=current_user["id"],
            stock_code=request.stock_code,
            stock_name=request.stock_name,
            market=request.market,
            quantity=request.quantity,
            avg_price=request.avg_price,
            buy_date=request.buy_date,
            notes=request.notes
        )

        return ok(holding, "添加持仓成功")
    except Exception as e:
        logger.error(f"添加持仓失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加持仓失败: {str(e)}"
        )


@router.put("/{holding_id}", response_model=dict)
async def update_holding(
    holding_id: str,
    request: UpdateHoldingRequest,
    current_user: dict = Depends(get_current_user)
):
    """更新持仓记录"""
    try:
        holding = await portfolio_service.update_holding(
            user_id=current_user["id"],
            holding_id=holding_id,
            quantity=request.quantity,
            avg_price=request.avg_price,
            buy_date=request.buy_date,
            notes=request.notes
        )

        if holding:
            return ok(holding, "更新持仓成功")
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="持仓记录不存在"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新持仓失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新持仓失败: {str(e)}"
        )


@router.delete("/{holding_id}", response_model=dict)
async def remove_holding(
    holding_id: str,
    current_user: dict = Depends(get_current_user)
):
    """删除持仓记录"""
    try:
        success = await portfolio_service.remove_holding(
            user_id=current_user["id"],
            holding_id=holding_id
        )

        if success:
            return ok({"id": holding_id}, "移除持仓成功")
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="持仓记录不存在"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"移除持仓失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"移除持仓失败: {str(e)}"
        )


@router.get("/{holding_id}", response_model=dict)
async def get_holding(
    holding_id: str,
    current_user: dict = Depends(get_current_user)
):
    """获取单条持仓记录"""
    try:
        holding = await portfolio_service.get_holding(
            user_id=current_user["id"],
            holding_id=holding_id
        )

        if holding:
            return ok(holding)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="持仓记录不存在"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取持仓失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取持仓失败: {str(e)}"
        )


# ==================== 基金持仓管理 ====================

class AddFundHoldingRequest(BaseModel):
    """添加基金持仓请求"""
    fund_code: str
    fund_name: str
    fund_type: str = "混合型"
    quantity: float
    avg_nav: float
    buy_date: str
    notes: str = ""


class UpdateFundHoldingRequest(BaseModel):
    """更新基金持仓请求"""
    quantity: Optional[float] = None
    avg_nav: Optional[float] = None
    buy_date: Optional[str] = None
    notes: Optional[str] = None


@router.get("/fund/", response_model=dict)
async def get_fund_holdings(
    current_user: dict = Depends(get_current_user)
):
    """获取用户基金持仓列表"""
    try:
        holdings = await portfolio_service.get_user_fund_holdings(current_user["id"])
        return ok(holdings)
    except Exception as e:
        logger.error(f"获取基金持仓列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取基金持仓列表失败: {str(e)}"
        )


@router.post("/fund/", response_model=dict)
async def add_fund_holding(
    request: AddFundHoldingRequest,
    current_user: dict = Depends(get_current_user)
):
    """添加基金持仓记录"""
    try:
        logger.info(
            f"添加基金持仓: user_id={current_user['id']}, "
            f"fund_code={request.fund_code}, quantity={request.quantity}"
        )

        holding = await portfolio_service.add_fund_holding(
            user_id=current_user["id"],
            fund_code=request.fund_code,
            fund_name=request.fund_name,
            fund_type=request.fund_type,
            quantity=request.quantity,
            avg_nav=request.avg_nav,
            buy_date=request.buy_date,
            notes=request.notes
        )

        return ok(holding, "添加基金持仓成功")
    except Exception as e:
        logger.error(f"添加基金持仓失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加基金持仓失败: {str(e)}"
        )


@router.put("/fund/{holding_id}", response_model=dict)
async def update_fund_holding(
    holding_id: str,
    request: UpdateFundHoldingRequest,
    current_user: dict = Depends(get_current_user)
):
    """更新基金持仓记录"""
    try:
        holding = await portfolio_service.update_fund_holding(
            user_id=current_user["id"],
            holding_id=holding_id,
            quantity=request.quantity,
            avg_nav=request.avg_nav,
            buy_date=request.buy_date,
            notes=request.notes
        )

        if holding:
            return ok(holding, "更新基金持仓成功")
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="基金持仓记录不存在"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新基金持仓失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新基金持仓失败: {str(e)}"
        )


@router.delete("/fund/{holding_id}", response_model=dict)
async def remove_fund_holding(
    holding_id: str,
    current_user: dict = Depends(get_current_user)
):
    """删除基金持仓记录"""
    try:
        success = await portfolio_service.remove_fund_holding(
            user_id=current_user["id"],
            holding_id=holding_id
        )

        if success:
            return ok({"id": holding_id}, "移除基金持仓成功")
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="基金持仓记录不存在"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"移除基金持仓失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"移除基金持仓失败: {str(e)}"
        )


@router.get("/fund/{holding_id}", response_model=dict)
async def get_fund_holding(
    holding_id: str,
    current_user: dict = Depends(get_current_user)
):
    """获取单条基金持仓记录"""
    try:
        holding = await portfolio_service.get_fund_holding(
            user_id=current_user["id"],
            holding_id=holding_id
        )

        if holding:
            return ok(holding)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="基金持仓记录不存在"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取基金持仓失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取基金持仓失败: {str(e)}"
        )
