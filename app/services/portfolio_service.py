"""
投资组合服务
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId

from app.core.database import get_mongo_db
from app.models.portfolio import PortfolioHolding


class PortfolioService:
    """投资组合服务类"""

    def __init__(self):
        self.db = None

    async def _get_db(self):
        """获取数据库连接"""
        if self.db is None:
            self.db = get_mongo_db()
        return self.db

    def _format_holding(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """格式化持仓记录为响应格式"""
        created_at = doc.get("created_at")
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()

        updated_at = doc.get("updated_at")
        if isinstance(updated_at, datetime):
            updated_at = updated_at.isoformat()

        return {
            "id": str(doc.get("_id")),
            "stock_code": doc.get("stock_code"),
            "stock_name": doc.get("stock_name"),
            "market": doc.get("market", "A股"),
            "quantity": doc.get("quantity", 0),
            "avg_price": doc.get("avg_price", 0.0),
            "buy_date": doc.get("buy_date", ""),
            "notes": doc.get("notes", ""),
            "created_at": created_at,
            "updated_at": updated_at,
        }

    async def get_user_holdings(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户持仓列表"""
        db = await self._get_db()
        collection = db.portfolio_holdings

        cursor = collection.find({"user_id": user_id}).sort("created_at", -1)
        docs = await cursor.to_list(length=None)
        return [self._format_holding(doc) for doc in docs]

    async def add_holding(
        self,
        user_id: str,
        stock_code: str,
        stock_name: str,
        market: str,
        quantity: int,
        avg_price: float,
        buy_date: str,
        notes: str = ""
    ) -> Dict[str, Any]:
        """添加持仓记录"""
        db = await self._get_db()
        collection = db.portfolio_holdings

        now = datetime.utcnow()
        doc = {
            "user_id": user_id,
            "stock_code": stock_code,
            "stock_name": stock_name,
            "market": market,
            "quantity": quantity,
            "avg_price": avg_price,
            "buy_date": buy_date,
            "notes": notes,
            "created_at": now,
            "updated_at": now,
        }

        result = await collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._format_holding(doc)

    async def update_holding(
        self,
        user_id: str,
        holding_id: str,
        quantity: Optional[int] = None,
        avg_price: Optional[float] = None,
        buy_date: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """更新持仓记录"""
        db = await self._get_db()
        collection = db.portfolio_holdings

        update_fields = {"updated_at": datetime.utcnow()}
        if quantity is not None:
            update_fields["quantity"] = quantity
        if avg_price is not None:
            update_fields["avg_price"] = avg_price
        if buy_date is not None:
            update_fields["buy_date"] = buy_date
        if notes is not None:
            update_fields["notes"] = notes

        result = await collection.find_one_and_update(
            {"_id": ObjectId(holding_id), "user_id": user_id},
            {"$set": update_fields},
            return_document=True
        )

        if result:
            return self._format_holding(result)
        return None

    async def remove_holding(self, user_id: str, holding_id: str) -> bool:
        """删除持仓记录"""
        db = await self._get_db()
        collection = db.portfolio_holdings

        result = await collection.delete_one(
            {"_id": ObjectId(holding_id), "user_id": user_id}
        )
        return result.deleted_count > 0

    async def get_holding(self, user_id: str, holding_id: str) -> Optional[Dict[str, Any]]:
        """获取单条持仓记录"""
        db = await self._get_db()
        collection = db.portfolio_holdings

        doc = await collection.find_one(
            {"_id": ObjectId(holding_id), "user_id": user_id}
        )
        if doc:
            return self._format_holding(doc)
        return None


    # ==================== 基金持仓 ====================

    def _format_fund_holding(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """格式化基金持仓记录为响应格式"""
        created_at = doc.get("created_at")
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()

        updated_at = doc.get("updated_at")
        if isinstance(updated_at, datetime):
            updated_at = updated_at.isoformat()

        return {
            "id": str(doc.get("_id")),
            "fund_code": doc.get("fund_code"),
            "fund_name": doc.get("fund_name"),
            "fund_type": doc.get("fund_type", "混合型"),
            "quantity": doc.get("quantity", 0.0),
            "avg_nav": doc.get("avg_nav", 0.0),
            "buy_date": doc.get("buy_date", ""),
            "notes": doc.get("notes", ""),
            "created_at": created_at,
            "updated_at": updated_at,
        }

    async def get_user_fund_holdings(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户基金持仓列表"""
        db = await self._get_db()
        collection = db.fund_holdings

        cursor = collection.find({"user_id": user_id}).sort("created_at", -1)
        docs = await cursor.to_list(length=None)
        return [self._format_fund_holding(doc) for doc in docs]

    async def add_fund_holding(
        self,
        user_id: str,
        fund_code: str,
        fund_name: str,
        fund_type: str,
        quantity: float,
        avg_nav: float,
        buy_date: str,
        notes: str = ""
    ) -> Dict[str, Any]:
        """添加基金持仓记录"""
        db = await self._get_db()
        collection = db.fund_holdings

        now = datetime.utcnow()
        doc = {
            "user_id": user_id,
            "fund_code": fund_code,
            "fund_name": fund_name,
            "fund_type": fund_type,
            "quantity": quantity,
            "avg_nav": avg_nav,
            "buy_date": buy_date,
            "notes": notes,
            "created_at": now,
            "updated_at": now,
        }

        result = await collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._format_fund_holding(doc)

    async def update_fund_holding(
        self,
        user_id: str,
        holding_id: str,
        quantity: Optional[float] = None,
        avg_nav: Optional[float] = None,
        buy_date: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """更新基金持仓记录"""
        db = await self._get_db()
        collection = db.fund_holdings

        update_fields = {"updated_at": datetime.utcnow()}
        if quantity is not None:
            update_fields["quantity"] = quantity
        if avg_nav is not None:
            update_fields["avg_nav"] = avg_nav
        if buy_date is not None:
            update_fields["buy_date"] = buy_date
        if notes is not None:
            update_fields["notes"] = notes

        result = await collection.find_one_and_update(
            {"_id": ObjectId(holding_id), "user_id": user_id},
            {"$set": update_fields},
            return_document=True
        )

        if result:
            return self._format_fund_holding(result)
        return None

    async def remove_fund_holding(self, user_id: str, holding_id: str) -> bool:
        """删除基金持仓记录"""
        db = await self._get_db()
        collection = db.fund_holdings

        result = await collection.delete_one(
            {"_id": ObjectId(holding_id), "user_id": user_id}
        )
        return result.deleted_count > 0

    async def get_fund_holding(self, user_id: str, holding_id: str) -> Optional[Dict[str, Any]]:
        """获取单条基金持仓记录"""
        db = await self._get_db()
        collection = db.fund_holdings

        doc = await collection.find_one(
            {"_id": ObjectId(holding_id), "user_id": user_id}
        )
        if doc:
            return self._format_fund_holding(doc)
        return None


    # ==================== 现金管理 ====================

    def _format_cash(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """格式化现金记录为响应格式"""
        created_at = doc.get("created_at")
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        updated_at = doc.get("updated_at")
        if isinstance(updated_at, datetime):
            updated_at = updated_at.isoformat()

        return {
            "id": str(doc.get("_id")),
            "currency": doc.get("currency", "CNY"),
            "amount": doc.get("amount", 0.0),
            "notes": doc.get("notes", ""),
            "created_at": created_at,
            "updated_at": updated_at,
        }

    async def get_user_cash(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户现金列表"""
        db = await self._get_db()
        collection = db.portfolio_cash
        cursor = collection.find({"user_id": user_id}).sort("created_at", -1)
        docs = await cursor.to_list(length=None)
        return [self._format_cash(doc) for doc in docs]

    async def add_cash(
        self,
        user_id: str,
        currency: str,
        amount: float,
        notes: str = ""
    ) -> Dict[str, Any]:
        """添加现金记录"""
        db = await self._get_db()
        collection = db.portfolio_cash

        now = datetime.utcnow()
        doc = {
            "user_id": user_id,
            "currency": currency,
            "amount": amount,
            "notes": notes,
            "created_at": now,
            "updated_at": now,
        }

        result = await collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._format_cash(doc)

    async def update_cash(
        self,
        user_id: str,
        cash_id: str,
        currency: Optional[str] = None,
        amount: Optional[float] = None,
        notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """更新现金记录"""
        db = await self._get_db()
        collection = db.portfolio_cash

        update_fields = {"updated_at": datetime.utcnow()}
        if currency is not None:
            update_fields["currency"] = currency
        if amount is not None:
            update_fields["amount"] = amount
        if notes is not None:
            update_fields["notes"] = notes

        result = await collection.find_one_and_update(
            {"_id": ObjectId(cash_id), "user_id": user_id},
            {"$set": update_fields},
            return_document=True
        )
        if result:
            return self._format_cash(result)
        return None

    async def remove_cash(self, user_id: str, cash_id: str) -> bool:
        """删除现金记录"""
        db = await self._get_db()
        collection = db.portfolio_cash
        result = await collection.delete_one(
            {"_id": ObjectId(cash_id), "user_id": user_id}
        )
        return result.deleted_count > 0


    # ==================== 实物资产管理 ====================

    def _format_asset(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """格式化实物资产记录为响应格式"""
        created_at = doc.get("created_at")
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        updated_at = doc.get("updated_at")
        if isinstance(updated_at, datetime):
            updated_at = updated_at.isoformat()

        return {
            "id": str(doc.get("_id")),
            "name": doc.get("name", ""),
            "quantity": doc.get("quantity", 0.0),
            "unit": doc.get("unit", "件"),
            "estimated_value": doc.get("estimated_value", 0.0),
            "notes": doc.get("notes", ""),
            "created_at": created_at,
            "updated_at": updated_at,
        }

    async def get_user_assets(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户实物资产列表"""
        db = await self._get_db()
        collection = db.portfolio_assets
        cursor = collection.find({"user_id": user_id}).sort("created_at", -1)
        docs = await cursor.to_list(length=None)
        return [self._format_asset(doc) for doc in docs]

    async def add_asset(
        self,
        user_id: str,
        name: str,
        quantity: float,
        unit: str = "件",
        estimated_value: float = 0.0,
        notes: str = ""
    ) -> Dict[str, Any]:
        """添加实物资产记录"""
        db = await self._get_db()
        collection = db.portfolio_assets
        now = datetime.utcnow()
        doc = {
            "user_id": user_id,
            "name": name,
            "quantity": quantity,
            "unit": unit,
            "estimated_value": estimated_value,
            "notes": notes,
            "created_at": now,
            "updated_at": now,
        }
        result = await collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._format_asset(doc)

    async def update_asset(
        self,
        user_id: str,
        asset_id: str,
        name: Optional[str] = None,
        quantity: Optional[float] = None,
        unit: Optional[str] = None,
        estimated_value: Optional[float] = None,
        notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """更新实物资产记录"""
        db = await self._get_db()
        collection = db.portfolio_assets
        update_fields = {"updated_at": datetime.utcnow()}
        if name is not None:
            update_fields["name"] = name
        if quantity is not None:
            update_fields["quantity"] = quantity
        if unit is not None:
            update_fields["unit"] = unit
        if estimated_value is not None:
            update_fields["estimated_value"] = estimated_value
        if notes is not None:
            update_fields["notes"] = notes
        result = await collection.find_one_and_update(
            {"_id": ObjectId(asset_id), "user_id": user_id},
            {"$set": update_fields},
            return_document=True
        )
        if result:
            return self._format_asset(result)
        return None

    async def remove_asset(self, user_id: str, asset_id: str) -> bool:
        """删除实物资产记录"""
        db = await self._get_db()
        collection = db.portfolio_assets
        result = await collection.delete_one(
            {"_id": ObjectId(asset_id), "user_id": user_id}
        )
        return result.deleted_count > 0


# 单例
portfolio_service = PortfolioService()
