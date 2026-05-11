"""
基金数据适配器
- 搜索：优先 AKShare（免费、无需Token）
- 详情：优先 Tushare（字段完整：费率、规模、经理等），Tushare失败时降级到AKShare
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd

logger = logging.getLogger("app.services.fund_data_adapter")


class FundDataAdapter:
    """基金数据适配器"""

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
        1. 优先尝试 AKShare（免费、快速）
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
                df = self._ak.fund_name_em()
                if df.empty:
                    return []

                # AKShare fund_name_em 列名是中文
                # 典型列：基金代码、基金简称、基金类型、日期、单位净值、累计净值、日增长率...
                keyword_lower = keyword.lower()

                # 动态查找列
                code_col = self._find_col(df, ['基金代码', 'code', '代码'])
                name_col = self._find_col(df, ['基金简称', 'name', '简称', '名称'])
                type_col = self._find_col(df, ['基金类型', '类型', 'fund_type'])

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
                        "fund_type": str(row.get(type_col, '')).strip() if type_col else None,
                        "market": "O",
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
        1. 优先尝试 Tushare（字段完整：费率、规模、经理等）
        2. Tushare 失败时降级到 AKShare（基础信息+净值）
        """
        result = {
            "ts_code": ts_code,
            "basic": {},
            "latest_nav": None,
            "latest_share": None,
            "managers": [],
        }

        tushare_success = False
        try:
            logger.info(f"🔄 [FundDataAdapter] 尝试使用 Tushare 获取基金详情: {ts_code}")
            tushare_ok = await self._fill_detail_with_tushare(ts_code, result)
            if tushare_ok:
                tushare_success = True
                logger.info(f"✅ [FundDataAdapter] Tushare 获取详情成功: {ts_code}")
            else:
                logger.warning(f"⚠️ [FundDataAdapter] Tushare 未返回有效数据，尝试 AKShare")
        except Exception as e:
            logger.warning(f"⚠️ [FundDataAdapter] Tushare 获取详情失败: {e}，尝试 AKShare")

        if not tushare_success and self._akshare_available:
            try:
                logger.info(f"🔄 [FundDataAdapter] 使用 AKShare 获取基金详情: {ts_code}")
                await self._fill_detail_with_akshare(ts_code, result)
                logger.info(f"✅ [FundDataAdapter] AKShare 获取详情成功: {ts_code}")
            except Exception as e:
                logger.error(f"❌ [FundDataAdapter] AKShare 获取详情也失败: {e}")

        return result

    async def _fill_detail_with_tushare(self, ts_code: str, result: Dict[str, Any]) -> bool:
        """使用 Tushare 填充基金详情，返回是否成功获取到有效数据"""
        tushare = self._get_tushare()
        has_data = False

        # Tushare 的 ts_code 格式为 "501050.SH"，但传入的可能是 "501050"
        # 构建候选代码列表
        candidates = [ts_code]
        if '.' not in ts_code:
            # 尝试加后缀
            candidates.extend([f"{ts_code}.SH", f"{ts_code}.SZ", f"{ts_code}.OF"])

        # 1. 基础信息（尝试多个候选代码）
        try:
            basic_df = await asyncio.to_thread(tushare.get_fund_basic)
            if not basic_df.empty:
                fund_row = None
                for cand in candidates:
                    matched = basic_df[basic_df['ts_code'] == cand]
                    if not matched.empty:
                        fund_row = matched
                        break

                # 如果没精确匹配，尝试前缀匹配
                if fund_row is None:
                    for cand in candidates:
                        matched = basic_df[basic_df['ts_code'].str.startswith(cand, na=False)]
                        if not matched.empty:
                            fund_row = matched
                            break

                if fund_row is not None and not fund_row.empty:
                    has_data = True
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

        # 2. 最新净值（同样尝试多个候选代码）
        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
            nav_df = None
            for cand in candidates:
                try:
                    nav_df = await asyncio.to_thread(tushare.get_fund_nav, cand, start_date, end_date)
                    if nav_df is not None and not nav_df.empty:
                        break
                except Exception:
                    continue

            if nav_df is not None and not nav_df.empty:
                has_data = True
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
            share_df = None
            for cand in candidates:
                try:
                    share_df = await asyncio.to_thread(tushare.get_fund_share, cand, start_date, end_date)
                    if share_df is not None and not share_df.empty:
                        break
                except Exception:
                    continue

            if share_df is not None and not share_df.empty:
                has_data = True
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
            manager_df = None
            for cand in candidates:
                try:
                    manager_df = await asyncio.to_thread(tushare.get_fund_manager, ts_code=cand)
                    if manager_df is not None and not manager_df.empty:
                        break
                except Exception:
                    continue

            if manager_df is not None and not manager_df.empty:
                has_data = True
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

        return has_data

    async def _fill_detail_with_akshare(self, ts_code: str, result: Dict[str, Any]):
        """使用 AKShare 填充基金详情（有限数据）"""
        def _do_fill():
            # 1. 基础信息 + 最新净值（fund_name_em 一张表就包含）
            try:
                df = self._ak.fund_name_em()
                if not df.empty:
                    code_col = self._find_col(df, ['基金代码', 'code', '代码'])
                    name_col = self._find_col(df, ['基金简称', 'name', '简称', '名称'])
                    type_col = self._find_col(df, ['基金类型', '类型', 'fund_type'])
                    nav_col = self._find_col(df, ['单位净值', 'nav', '净值'])
                    acc_nav_col = self._find_col(df, ['累计净值', 'acc_nav'])
                    date_col = self._find_col(df, ['日期', 'date', 'nav_date'])
                    daily_return_col = self._find_col(df, ['日增长率', '日涨幅', 'daily_return'])

                    if code_col:
                        # AKShare 的代码是纯数字，不带后缀
                        matched = df[df[code_col].astype(str).str.strip() == ts_code.strip()]
                        if matched.empty and '.' in ts_code:
                            # 如果传入的是带后缀的，尝试去掉后缀
                            pure_code = ts_code.split('.')[0]
                            matched = df[df[code_col].astype(str).str.strip() == pure_code]

                        if not matched.empty:
                            row = matched.iloc[0]
                            result["basic"] = {
                                "ts_code": ts_code,
                                "name": str(row.get(name_col, '')).strip() if name_col else ts_code,
                                "fund_type": str(row.get(type_col, '')).strip() if type_col else None,
                                "market": "O",
                                "status": "L",
                            }
                            # 净值
                            if nav_col:
                                nav_val = row.get(nav_col)
                                result["latest_nav"] = {
                                    "nav_date": str(row.get(date_col, '')).strip() if date_col else None,
                                    "nav": float(nav_val) if pd.notna(nav_val) else None,
                                    "acc_nav": float(row.get(acc_nav_col)) if acc_nav_col and pd.notna(row.get(acc_nav_col)) else None,
                                    "daily_return": float(row.get(daily_return_col)) / 100 if daily_return_col and pd.notna(row.get(daily_return_col)) else None,
                                }
            except Exception as e:
                logger.warning(f"⚠️ [AKShare] 基础信息+净值获取失败: {e}")

            # 2. 尝试获取更详细的信息（如 fund_individual_basic_info_xq）
            try:
                # 雪球基金详情
                detail_df = self._ak.fund_individual_basic_info_xq(symbol=ts_code)
                if detail_df is not None and not detail_df.empty:
                    row = detail_df.iloc[0]
                    # 合并到 basic
                    if not result.get("basic"):
                        result["basic"] = {"ts_code": ts_code}
                    result["basic"]["management"] = result["basic"].get("management") or str(row.get("管理人", row.get("management", ""))).strip() or None
                    result["basic"]["custodian"] = result["basic"].get("custodian") or str(row.get("托管人", row.get("custodian", ""))).strip() or None
                    result["basic"]["found_date"] = result["basic"].get("found_date") or str(row.get("成立日期", row.get("found_date", ""))).strip() or None
                    result["basic"]["benchmark"] = result["basic"].get("benchmark") or str(row.get("业绩基准", row.get("benchmark", ""))).strip() or None
            except Exception as e:
                logger.debug(f"[AKShare] 雪球详情获取失败（非关键）: {e}")

        await asyncio.to_thread(_do_fill)

    @staticmethod
    def _find_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        """在 DataFrame 列中查找匹配的列名"""
        for col in df.columns:
            for cand in candidates:
                if cand in str(col):
                    return col
        return None


# 全局适配器实例
_fund_data_adapter = None


def get_fund_data_adapter() -> FundDataAdapter:
    """获取全局基金数据适配器实例"""
    global _fund_data_adapter
    if _fund_data_adapter is None:
        _fund_data_adapter = FundDataAdapter()
    return _fund_data_adapter
