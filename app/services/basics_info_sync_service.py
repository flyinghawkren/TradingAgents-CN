"""
基础信息同步服务
定期从数据源获取股票和基金基础信息，存入本地 MongoDB
用于搜索补全等高频场景
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.core.database import get_mongo_db

logger = logging.getLogger("app.services.basics_info_sync")


class BasicsInfoSyncService:
    """基础信息同步服务"""

    def __init__(self):
        self._running = False
        self._last_sync_time: Optional[datetime] = None
        self._last_result: Optional[Dict[str, Any]] = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_sync_time(self) -> Optional[datetime]:
        return self._last_sync_time

    @property
    def last_result(self) -> Optional[Dict[str, Any]]:
        return self._last_result

    async def sync_all(self, force: bool = False) -> Dict[str, Any]:
        """
        同步所有基础信息（股票 + 基金）

        Args:
            force: 是否强制同步（忽略运行中状态）

        Returns:
            同步结果统计
        """
        if self._running and not force:
            logger.warning("⚠️ 基础信息同步已在运行中，跳过本次请求")
            return {"success": False, "message": "同步已在运行中", "already_running": True}

        self._running = True
        start_time = datetime.utcnow()
        result = {"stock": {}, "fund": {}, "success": False}

        try:
            logger.info("🔄 开始基础信息全量同步...")

            # 同步股票基础信息
            stock_result = await self._sync_stock_basics()
            result["stock"] = stock_result

            # 同步基金基础信息
            fund_result = await self._sync_fund_basics()
            result["fund"] = fund_result

            result["success"] = True
            result["message"] = (
                f"同步完成：股票 {stock_result.get('count', 0)} 条，"
                f"基金 {fund_result.get('count', 0)} 条"
            )

            elapsed = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"✅ 基础信息同步完成，耗时 {elapsed:.1f}s")

        except Exception as e:
            logger.error(f"❌ 基础信息同步失败: {e}", exc_info=True)
            result["success"] = False
            result["message"] = f"同步失败: {str(e)}"
        finally:
            self._running = False
            self._last_sync_time = datetime.utcnow()
            self._last_result = result

        return result

    async def _sync_stock_basics(self) -> Dict[str, Any]:
        """同步股票基础信息"""
        result = {"count": 0, "message": ""}
        try:
            db = get_mongo_db()
            collection = db.stock_basics

            # 优先使用 Tushare，降级到 AKShare
            stocks = []
            try:
                from tradingagents.dataflows.providers.china.tushare import get_tushare_provider
                tushare = get_tushare_provider()
                if tushare:
                    df = await asyncio.to_thread(tushare.get_stock_basic)
                    if df is not None and not df.empty:
                        for _, row in df.iterrows():
                            stocks.append({
                                "ts_code": row.get("ts_code", ""),
                                "symbol": row.get("symbol", ""),
                                "name": row.get("name", ""),
                                "market": row.get("market", ""),
                                "industry": row.get("industry", ""),
                                "area": row.get("area", ""),
                                "list_date": row.get("list_date", ""),
                                "updated_at": datetime.utcnow(),
                            })
                        logger.info(f"📊 Tushare 股票基础信息: {len(stocks)} 条")
            except Exception as e:
                logger.warning(f"⚠️ Tushare 股票基础信息获取失败: {e}")

            # Tushare 失败时降级到 AKShare
            if not stocks:
                try:
                    import akshare as ak
                    df = await asyncio.to_thread(ak.stock_zh_a_spot_em)
                    if df is not None and not df.empty:
                        for _, row in df.head(5000).iterrows():
                            code = str(row.get("代码", ""))
                            name = str(row.get("名称", ""))
                            if code and name:
                                stocks.append({
                                    "ts_code": code,
                                    "symbol": code,
                                    "name": name,
                                    "market": "",
                                    "industry": "",
                                    "area": "",
                                    "list_date": "",
                                    "updated_at": datetime.utcnow(),
                                })
                        logger.info(f"📊 AKShare 股票基础信息: {len(stocks)} 条")
                except Exception as e:
                    logger.warning(f"⚠️ AKShare 股票基础信息获取失败: {e}")

            if stocks:
                # 清空旧数据，写入新数据
                await collection.delete_many({})
                await collection.insert_many(stocks)
                # 创建索引
                await collection.create_index("ts_code", unique=True)
                await collection.create_index("symbol")
                await collection.create_index("name")

            result["count"] = len(stocks)
            result["message"] = f"股票基础信息: {len(stocks)} 条"

        except Exception as e:
            logger.error(f"❌ 股票基础信息同步失败: {e}", exc_info=True)
            result["message"] = f"失败: {str(e)}"

        return result

    async def _sync_fund_basics(self) -> Dict[str, Any]:
        """同步基金基础信息"""
        result = {"count": 0, "message": ""}
        try:
            db = get_mongo_db()
            collection = db.fund_basics

            funds = []
            try:
                import akshare as ak
                df = await asyncio.to_thread(ak.fund_name_em)
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        code = str(row.get("基金代码", row.get("code", "")))
                        name = str(row.get("基金简称", row.get("name", "")))
                        ftype = str(row.get("基金类型", row.get("类型", "")))
                        if code and name:
                            funds.append({
                                "ts_code": code,
                                "name": name,
                                "fund_type": ftype,
                                "updated_at": datetime.utcnow(),
                            })
                    logger.info(f"📊 AKShare 基金基础信息: {len(funds)} 条")
            except Exception as e:
                logger.warning(f"⚠️ AKShare 基金基础信息获取失败: {e}")
                # 降级到 Tushare
                try:
                    from tradingagents.dataflows.providers.china.tushare import get_tushare_provider
                    tushare = get_tushare_provider()
                    if tushare:
                        df = await asyncio.to_thread(tushare.get_fund_basic)
                        if df is not None and not df.empty:
                            for _, row in df.iterrows():
                                funds.append({
                                    "ts_code": row.get("ts_code", ""),
                                    "name": row.get("name", ""),
                                    "fund_type": row.get("fund_type", ""),
                                    "updated_at": datetime.utcnow(),
                                })
                            logger.info(f"📊 Tushare 基金基础信息: {len(funds)} 条")
                except Exception as e2:
                    logger.warning(f"⚠️ Tushare 基金基础信息获取失败: {e2}")

            if funds:
                await collection.delete_many({})
                await collection.insert_many(funds)
                await collection.create_index("ts_code", unique=True)
                await collection.create_index("name")

            result["count"] = len(funds)
            result["message"] = f"基金基础信息: {len(funds)} 条"

        except Exception as e:
            logger.error(f"❌ 基金基础信息同步失败: {e}", exc_info=True)
            result["message"] = f"失败: {str(e)}"

        return result

    async def get_stock_basics(self, keyword: str = "", limit: int = 20) -> List[Dict[str, Any]]:
        """查询股票基础信息（用于搜索补全）"""
        try:
            db = get_mongo_db()
            collection = db.stock_basics

            query = {}
            if keyword:
                keyword_lower = keyword.lower()
                query["$or"] = [
                    {"ts_code": {"$regex": keyword_lower, "$options": "i"}},
                    {"symbol": {"$regex": keyword_lower, "$options": "i"}},
                    {"name": {"$regex": keyword_lower, "$options": "i"}},
                ]

            cursor = collection.find(query).limit(limit)
            docs = await cursor.to_list(length=limit)
            return [{k: v for k, v in doc.items() if k != "_id"} for doc in docs]
        except Exception as e:
            logger.error(f"查询股票基础信息失败: {e}")
            return []

    async def get_fund_basics(self, keyword: str = "", limit: int = 20) -> List[Dict[str, Any]]:
        """查询基金基础信息（用于搜索补全）"""
        try:
            db = get_mongo_db()
            collection = db.fund_basics

            query = {}
            if keyword:
                keyword_lower = keyword.lower()
                query["$or"] = [
                    {"ts_code": {"$regex": keyword_lower, "$options": "i"}},
                    {"name": {"$regex": keyword_lower, "$options": "i"}},
                ]

            cursor = collection.find(query).limit(limit)
            docs = await cursor.to_list(length=limit)
            return [{k: v for k, v in doc.items() if k != "_id"} for doc in docs]
        except Exception as e:
            logger.error(f"查询基金基础信息失败: {e}")
            return []

    async def get_stats(self) -> Dict[str, Any]:
        """获取同步统计信息"""
        try:
            db = get_mongo_db()
            stock_count = await db.stock_basics.estimated_document_count()
            fund_count = await db.fund_basics.estimated_document_count()

            return {
                "is_running": self._running,
                "last_sync_time": self._last_sync_time.isoformat() if self._last_sync_time else None,
                "last_result": self._last_result,
                "stock_count": stock_count,
                "fund_count": fund_count,
            }
        except Exception as e:
            logger.error(f"获取同步统计失败: {e}")
            return {
                "is_running": self._running,
                "last_sync_time": None,
                "last_result": None,
                "stock_count": 0,
                "fund_count": 0,
            }


# 全局单例
_basics_info_sync_service: Optional[BasicsInfoSyncService] = None


def get_basics_info_sync_service() -> BasicsInfoSyncService:
    """获取基础信息同步服务单例"""
    global _basics_info_sync_service
    if _basics_info_sync_service is None:
        _basics_info_sync_service = BasicsInfoSyncService()
    return _basics_info_sync_service
