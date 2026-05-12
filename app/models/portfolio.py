"""
投资组合持仓数据模型
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.utils.timezone import now_tz


class PortfolioHolding(BaseModel):
    """持仓记录模型"""
    id: Optional[str] = Field(None, description="持仓记录ID")
    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    market: str = Field(default="A股", description="市场类型")
    quantity: int = Field(..., ge=1, description="持有数量")
    avg_price: float = Field(..., ge=0, description="买进均价")
    buy_date: str = Field(..., description="买进时间 (YYYY-MM-DD)")
    notes: str = Field(default="", description="备注")
    created_at: Optional[datetime] = Field(default_factory=now_tz, description="创建时间")
    updated_at: Optional[datetime] = Field(default_factory=now_tz, description="更新时间")


class AddHoldingRequest(BaseModel):
    """添加持仓请求"""
    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    market: str = Field(default="A股", description="市场类型")
    quantity: int = Field(..., ge=1, description="持有数量")
    avg_price: float = Field(..., ge=0, description="买进均价")
    buy_date: str = Field(..., description="买进时间 (YYYY-MM-DD)")
    notes: str = Field(default="", description="备注")


class UpdateHoldingRequest(BaseModel):
    """更新持仓请求"""
    quantity: Optional[int] = Field(None, ge=1, description="持有数量")
    avg_price: Optional[float] = Field(None, ge=0, description="买进均价")
    buy_date: Optional[str] = Field(None, description="买进时间 (YYYY-MM-DD)")
    notes: Optional[str] = Field(None, description="备注")


class HoldingResponse(BaseModel):
    """持仓响应"""
    id: str
    stock_code: str
    stock_name: str
    market: str
    quantity: int
    avg_price: float
    buy_date: str
    notes: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
