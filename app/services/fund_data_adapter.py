"""
基金数据适配器
优先使用 AKShare，AKShare 失败时降级到 Tushare
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd

logger = logging.getLogger("app.services.fund_data_adapter")


class FundDataAdapter:
    """基金数据适配器：优先 AKShare，降级 Tushare"""

    def __init__(self):
        self._tushare = None
        self._akshare_available = False
        self._ak = None
        self._try_init_akshare()

    def _try_init_akshare(self):
        """尝试初始化 AKShare"""
        try:
            import akshare as ak
            self._ak = ak
            self._akshare_available = True
            logger.info("✅ [FundDataAdapter] AKShare 初始化成功")
        except ImportError:
            self._akshare_available = False
            logger.warning("⚠️ [FundDataAdapter] AKShare 未安装")

    def _get_tushare(self):
        """获取 Tushare provider（延迟加载）"""
        if self._tushare is None:
            from tradingagents.dataflows.providers.china.tushare import get_tushare_provider
            self._tushare = get_tushare_provider()
        return self._tushare

    # ==================== 搜索基金 ====================

    async def search_funds(self, keyword: str, market: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        搜索基金
        1. 优先尝试 AKShare
        2. AKShare 失败时降级到 Tushare
        """
        if self._akshare_available:
            try:
                logger.info(f"🔄 [FundDataAdapter] 尝试使用 AKShare 搜索基金: {keyword}")
                result = await self._search_with_akshare(keyword, limit)
                if result:
                    logger.info(f"✅ [FundDataAdapter] AKShare 搜索成功，找到 {len(result)} 只基金")
                    return result
                logger.warning(f"⚠️ [FundDataAdapter] AKShare 搜索无结果，尝试 Tushare")
            except Exception as e:
                logger.warning(f"⚠️ [FundDataAdapter] AKShare 搜索失败: {e}，尝试 Tushare")

        # 降级到 Tushare
        try:
            logger.info(f"🔄 [FundDataAdapter] 使用 Tushare 搜索基金: {keyword}")
            return await self._search_with_tushare(keyword, market, limit)
        except Exception as e:
            logger.error(f"❌ [FundDataAdapter] Tushare 搜索也失败: {e}")
            return []

    async def _search_with_akshare(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """使用 AKShare 搜索基金"""
        def _do_search():
            try:
                # 获取基金列表
                df = self._ak.fund_name_em()
                if df.empty:
                    return []

                # 模糊搜索（支持代码和名称）
                keyword_lower = keyword.lower()

                # 处理列名兼容性
                code_col = None
                name_col = None
                for col in df.columns:
                    if 'code' in col.lower() or '代码' in col:
                        code_col = col
                    if 'name' in col.lower() or '名称' in col or '简称' in col:
                        name_col = col

                if code_col is None or name_col is None:
                    logger.warning(f"⚠️ [AKShare] 基金搜索列名不匹配，可用列: {list(df.columns)}")
                    return []

                matched = df[
                    df[code_col].astype(str).str.lower().str.contains(keyword_lower, na=False) |
                    df[name_col].astype(str).str.lower().str.contains(keyword_lower, na=False)
                ]

                funds = []
                for _, row in matched.head(limit).iterrows():
                    funds.append({
                        "ts_code": str(row.get(code_col, '')).strip(),
                        "name": str(row.get(name_col, '')).strip(),
                        "fund_type": str(row.get("类型", row.get("fund_type", ""))).strip() or None,
                        "market": "O",  # AKShare 的 fund_name_em 主要是场外基金
                        "status": "L",
                        "management": None,
                    })
                return funds
            except Exception as e:
                logger.error(f"❌ [AKShare] 基金搜索内部错误: {e}")
                raise

        return await asyncio.to_thread(_do_search)

    async def _search_with_tushare(self, keyword: str, market: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """使用 Tushare 搜索基金"""
        tushare = self._get_tushare()
        df = await asyncio.to_thread(tushare.get_fund_basic, market=market)
        if df.empty:
            return []

        keyword_lower = keyword.lower()
        matched = df[
            df['ts_code'].str.lower().str.contains(keyword_lower, na=False) |
            df['name'].str.lower().str.contains(keyword_lower, na=False)
        ]

        funds = []
        for _, row in matched.head(limit).iterrows():
            funds.append({
                "ts_code": row.get("ts_code"),
                "name": row.get("name"),
                "fund_type": row.get("fund_type"),
                "market": row.get("market"),
                "status": row.get("status"),
                "management": row.get("management"),
            })
        return funds

    # ==================== 基金详情 ====================

    async def get_fund_detail(self, ts_code: str) -> Dict[str, Any]:
        """
        获取基金详情
        1. 优先尝试 AKShare
        2. AKShare 失败时降级到 Tushare
        """
        result = {
            "ts_code": ts_code,
            "basic": {},
            "latest_nav": None,
            "latest_share": None,
            "managers": [],
        }

        ak_success = False
        if self._akshare_available:
            try:
                logger.info(f"🔄 [FundDataAdapter] 尝试使用 AKShare 获取基金详情: {ts_code}")
                await self._fill_detail_with_akshare(ts_code, result)
                ak_success = True
                logger.info(f"✅ [FundDataAdapter] AKShare 获取详情成功: {ts_code}")
            except Exception as e:
                logger.warning(f"⚠️ [FundDataAdapter] AKShare 获取详情失败: {e}，尝试 Tushare")

        if not ak_success:
            try:
                logger.info(f"🔄 [FundDataAdapter] 使用 Tushare 获取基金详情: {ts_code}")
                await self._fill_detail_with_tushare(ts_code, result)
                logger.info(f"✅ [FundDataAdapter] Tushare 获取详情成功: {ts_code}")
            except Exception as e:
                logger.error(f"❌ [FundDataAdapter] Tushare 获取详情也失败: {e}")

        return result

    async def _fill_detail_with_akshare(self, ts_code: str, result: Dict[str, Any]):
        """使用 AKShare 填充基金详情"""
        def _do_fill():
            # 1. 基础信息
            try:
                # 尝试获取基金基本信息
                df = self._ak.fund_name_em()
                if not df.empty:
                    code_col = None
                    name_col = None
                    for col in df.columns:
                        if 'code' in col.lower() or '代码' in col:
                            code_col = col
                        if 'name' in col.lower() or '名称' in col or '简称' in col:
                            name_col = col

                    if code_col:
                        matched = df[df[code_col].astype(str).str.strip() == ts_code.strip()]
                        if not matched.empty:
                            row = matched.iloc[0]
                            result["basic"] = {
                                "ts_code": ts_code,
                                "name": str(row.get(name_col, '')).strip() if name_col else ts_code,
                                "fund_type": str(row.get("类型", row.get("fund_type", ""))).strip() or None,
                                "market": "O",
                                "status": "L",
                            }
            except Exception as e:
                logger.warning(f"⚠️ [AKShare] 基础信息获取失败: {e}")

            # 2. 最新净值
            try:
                # 尝试获取净值数据（不同 akshare 版本接口不同）
                nav_df = None
                try:
                    nav_df = self._ak.fund_open_fund_daily_em()
                    if nav_df is not None and not nav_df.empty:
                        code_col = [c for c in nav_df.columns if 'code' in c.lower() or '代码' in c][0]
                        matched = nav_df[nav_df[code_col].astype(str).str.strip() == ts_code.strip()]
                        if not matched.empty:
                            row = matched.iloc[0]
                            nav_col = [c for c in nav_df.columns if 'nav' in c.lower() or '净值' in c][0]
                            date_col = [c for c in nav_df.columns if 'date' in c.lower() or '日期' in c][0]
                            result["latest_nav"] = {
                                "nav_date": str(row.get(date_col, '')).strip(),
                                "nav": float(row.get(nav_col, 0)) if pd.notna(row.get(nav_col)) else None,
                            }
                except Exception:
                    pass

                if result["latest_nav"] is None:
                    # 尝试另一个接口
                    try:
                        nav_df = self._ak.fund_em_open_fund_info(fund=ts_code, indicator="单位净值走势")
                        if nav_df is not None and not nav_df.empty:
                            latest = nav_df.iloc[-1]
                            result["latest_nav"] = {
                                "nav_date": str(latest.iloc[0]) if len(latest) > 0 else None,
                                "nav": float(latest.iloc[1]) if len(latest) > 1 and pd.notna(latest.iloc[1]) else None,
                            }
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"⚠️ [AKShare] 净值获取失败: {e}")

        await asyncio.to_thread(_do_fill)

    async def _fill_detail_with_tushare(self, ts_code: str, result: Dict[str, Any]):
        """使用 Tushare 填充基金详情"""
        tushare = self._get_tushare()

        # 1. 基础信息
        try:
            basic_df = await asyncio.to_thread(tushare.get_fund_basic)
            if not basic_df.empty:
                fund_row = basic_df[basic_df['ts_code'] == ts_code]
                if not fund_row.empty:
                    row = fund_row.iloc[0]
                    result["basic"] = {
                        "ts_code": row.get("ts_code"),
                        "name": row.get("name"),
                        "short_name": row.get("short_name"),
                        "fund_type": row.get("fund_type"),
                        "market": row.get("market"),
                        "status": row.get("status"),
                        "found_date": row.get("found_date"),
                        "list_date": row.get("list_date"),
                        "invest_type": row.get("invest_type"),
                        "type": row.get("type"),
                        "management": row.get("management"),
                        "custodian": row.get("custodian"),
                        "benchmark": row.get("benchmark"),
                        "m_fee": row.get("m_fee"),
                        "c_fee": row.get("c_fee"),
                        "s_fee": row.get("s_fee"),
                        "p_fee": row.get("p_fee"),
                        "r_fee": row.get("r_fee"),
                    }
        except Exception as e:
            logger.warning(f"⚠️ [Tushare] 基础信息获取失败: {e}")

        # 2. 最新净值
        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
            nav_df = await asyncio.to_thread(tushare.get_fund_nav, ts_code, start_date, end_date)
            if nav_df is not None and not nav_df.empty:
                latest = nav_df.iloc[0]
                prev = nav_df.iloc[1] if len(nav_df) > 1 else None
                nav_val = latest.get("unit_nav") or latest.get("nav")
                prev_nav = prev.get("unit_nav") or prev.get("nav") if prev is not None else None
                daily_return = None
                if nav_val is not None and prev_nav is not None and prev_nav != 0:
                    daily_return = (nav_val - prev_nav) / prev_nav
                result["latest_nav"] = {
                    "nav_date": latest.get("nav_date") or latest.get("end_date"),
                    "nav": nav_val,
                    "acc_nav": latest.get("accum_nav") or latest.get("acc_nav"),
                    "daily_return": daily_return,
                }
        except Exception as e:
            logger.warning(f"⚠️ [Tushare] 净值获取失败: {e}")

        # 3. 最新规模
        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
            share_df = await asyncio.to_thread(tushare.get_fund_share, ts_code, start_date, end_date)
            if share_df is not None and not share_df.empty:
                latest_share = share_df.iloc[0]
                result["latest_share"] = {
                    "trade_date": latest_share.get("trade_date") or latest_share.get("ann_date"),
                    "fd_share": latest_share.get("fd_share") or latest_share.get("share"),
                    "fd_amount": latest_share.get("fd_amount") or latest_share.get("amount"),
                }
        except Exception as e:
            logger.warning(f"⚠️ [Tushare] 份额获取失败: {e}")

        # 4. 基金经理
        try:
            manager_df = await asyncio.to_thread(tushare.get_fund_manager, ts_code=ts_code)
            if manager_df is not None and not manager_df.empty:
                managers = []
                for _, row in manager_df.iterrows():
                    managers.append({
                        "name": row.get("name"),
                        "gender": row.get("gender"),
                        "birth_year": row.get("birth_year"),
                        "edu": row.get("edu") or row.get("education"),
                        "resume": row.get("resume") or row.get("intro"),
                        "begin_date": row.get("begin_date"),
                        "end_date": row.get("end_date"),
                    })
                result["managers"] = managers
        except Exception as e:
            logger.warning(f"⚠️ [Tushare] 基金经理获取失败: {e}")


# 全局适配器实例
_fund_data_adapter = None


def get_fund_data_adapter() -> FundDataAdapter:
    """获取全局基金数据适配器实例"""
    global _fund_data_adapter
    if _fund_data_adapter is None:
        _fund_data_adapter = FundDataAdapter()
    return _fund_data_adapter
