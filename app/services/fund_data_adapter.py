"""
基金数据适配器
- 搜索：优先 AKShare（免费、无需Token）
- 详情：优先 AKShare（字段有限但免费），AKShare 查不到的字段再降级 Tushare
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
        """搜索基金：优先 AKShare，降级 Tushare"""
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

                keyword_lower = keyword.lower()
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
        1. 优先 AKShare（免费、无频率限制）
        2. AKShare 查不到的字段，再用 Tushare 补充（有频率限制，尽量少调用）
        """
        result = {
            "ts_code": ts_code,
            "basic": {},
            "latest_nav": None,
            "latest_share": None,
            "managers": [],
        }

        # 第1步：AKShare 获取尽可能多的数据
        akshare_has_basic = False
        if self._akshare_available:
            try:
                logger.info(f"🔄 [FundDataAdapter] 使用 AKShare 获取基金详情: {ts_code}")
                akshare_has_basic = await self._fill_detail_with_akshare(ts_code, result)
                if akshare_has_basic:
                    logger.info(f"✅ [FundDataAdapter] AKShare 获取详情成功: {ts_code}")
            except Exception as e:
                logger.warning(f"⚠️ [FundDataAdapter] AKShare 获取详情失败: {e}")

        # 第2步：检查缺失字段，用 Tushare 补充
        missing_fields = self._check_missing_fields(result)
        if missing_fields:
            logger.info(f"🔄 [FundDataAdapter] AKShare 缺失字段 {missing_fields}，尝试用 Tushare 补充: {ts_code}")
            try:
                await self._fill_missing_with_tushare(ts_code, result, missing_fields)
                logger.info(f"✅ [FundDataAdapter] Tushare 补充完成: {ts_code}")
            except Exception as e:
                logger.warning(f"⚠️ [FundDataAdapter] Tushare 补充失败: {e}")

        return result

    def _check_missing_fields(self, result: Dict[str, Any]) -> List[str]:
        """检查哪些关键字段缺失"""
        missing = []
        basic = result.get("basic") or {}
        if not basic.get("management"):
            missing.append("management")
        if not basic.get("custodian"):
            missing.append("custodian")
        if not basic.get("found_date"):
            missing.append("found_date")
        if not basic.get("benchmark"):
            missing.append("benchmark")
        if not basic.get("m_fee"):
            missing.append("m_fee")
        if not basic.get("c_fee"):
            missing.append("c_fee")
        if result.get("latest_share") is None:
            missing.append("latest_share")
        if not result.get("managers"):
            missing.append("managers")
        return missing

    async def _fill_detail_with_akshare(self, ts_code: str, result: Dict[str, Any]) -> bool:
        """使用 AKShare 填充基金详情，返回是否获取到基础信息"""
        has_basic = False
        pure_code = ts_code.split('.')[0] if '.' in ts_code else ts_code

        def _do_fill():
            nonlocal has_basic

            # 1. fund_name_em：基础信息 + 最新净值
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
                            has_basic = True

                            # 净值
                            if nav_col:
                                nav_val = row.get(nav_col)
                                daily_ret = row.get(daily_return_col) if daily_return_col else None
                                result["latest_nav"] = {
                                    "nav_date": str(row.get(date_col, '')).strip() if date_col else None,
                                    "nav": float(nav_val) if pd.notna(nav_val) else None,
                                    "acc_nav": float(row.get(acc_nav_col)) if acc_nav_col and pd.notna(row.get(acc_nav_col)) else None,
                                    "daily_return": float(daily_ret) / 100 if daily_ret is not None and pd.notna(daily_ret) else None,
                                }
            except Exception as e:
                logger.warning(f"⚠️ [AKShare] fund_name_em 获取失败: {e}")

            # 2. fund_individual_basic_info_xq：雪球基金详情（管理人、托管人、成立日期、业绩基准、费率）
            try:
                detail_df = self._ak.fund_individual_basic_info_xq(symbol=pure_code)
                if detail_df is not None and not detail_df.empty:
                    row = detail_df.iloc[0]
                    if not result.get("basic"):
                        result["basic"] = {"ts_code": ts_code}
                        has_basic = True

                    b = result["basic"]
                    # 管理人
                    val = row.get("管理人") or row.get("management") or row.get("基金公司")
                    if val and pd.notna(val):
                        b["management"] = str(val).strip()

                    # 托管人
                    val = row.get("托管人") or row.get("custodian") or row.get("托管银行")
                    if val and pd.notna(val):
                        b["custodian"] = str(val).strip()

                    # 成立日期
                    val = row.get("成立日期") or row.get("found_date") or row.get("成立日")
                    if val and pd.notna(val):
                        b["found_date"] = str(val).strip()

                    # 业绩基准
                    val = row.get("业绩基准") or row.get("benchmark") or row.get("业绩比较基准")
                    if val and pd.notna(val):
                        b["benchmark"] = str(val).strip()

                    # 费率（尝试解析各种可能的字段名）
                    for fee_key, target_key in [
                        ("管理费", "m_fee"), ("管理费率", "m_fee"),
                        ("托管费", "c_fee"), ("托管费率", "c_fee"),
                        ("销售服务费", "s_fee"), ("销售服务费率", "s_fee"),
                        ("申购费", "p_fee"), ("申购费率", "p_fee"),
                        ("赎回费", "r_fee"), ("赎回费率", "r_fee"),
                    ]:
                        val = row.get(fee_key)
                        if val is not None and pd.notna(val) and target_key not in b:
                            try:
                                b[target_key] = float(val)
                            except (ValueError, TypeError):
                                pass
            except Exception as e:
                logger.debug(f"[AKShare] fund_individual_basic_info_xq 获取失败（非关键）: {e}")

            # 3. fund_individual_achievement_xq：雪球基金业绩（规模信息）
            try:
                achieve_df = self._ak.fund_individual_achievement_xq(symbol=pure_code)
                if achieve_df is not None and not achieve_df.empty:
                    row = achieve_df.iloc[0]
                    # 规模
                    scale_val = row.get("基金规模") or row.get("规模") or row.get("asset") or row.get("fund_size")
                    if scale_val is not None and pd.notna(scale_val):
                        try:
                            result["latest_share"] = {
                                "trade_date": str(row.get("日期", row.get("date", ""))).strip() or None,
                                "fd_share": None,
                                "fd_amount": float(scale_val),
                            }
                        except (ValueError, TypeError):
                            pass
            except Exception as e:
                logger.debug(f"[AKShare] fund_individual_achievement_xq 获取失败（非关键）: {e}")

            # 4. fund_manager_em：东方财富基金经理
            try:
                manager_df = self._ak.fund_manager_em()
                if manager_df is not None and not manager_df.empty:
                    code_col = self._find_col(manager_df, ['基金代码', '代码'])
                    if code_col:
                        matched = manager_df[manager_df[code_col].astype(str).str.strip() == pure_code]
                        if not matched.empty:
                            managers = []
                            for _, row in matched.iterrows():
                                mgr = {
                                    "name": str(row.get("姓名", row.get("name", ""))).strip() or None,
                                    "gender": str(row.get("性别", row.get("gender", ""))).strip() or None,
                                    "begin_date": str(row.get("任职日期", row.get("begin_date", ""))).strip() or None,
                                    "resume": str(row.get("基金经理简介", row.get("resume", ""))).strip() or None,
                                }
                                if mgr["name"]:
                                    managers.append(mgr)
                            if managers:
                                result["managers"] = managers
            except Exception as e:
                logger.debug(f"[AKShare] fund_manager_em 获取失败（非关键）: {e}")

        await asyncio.to_thread(_do_fill)
        return has_basic

    async def _fill_missing_with_tushare(self, ts_code: str, result: Dict[str, Any], missing_fields: List[str]):
        """使用 Tushare 补充缺失字段（尽量少调用，避免频率限制）"""
        tushare = self._get_tushare()
        candidates = [ts_code]
        if '.' not in ts_code:
            candidates.extend([f"{ts_code}.SH", f"{ts_code}.SZ", f"{ts_code}.OF"])

        # 1. 基础信息（管理人、托管人、费率等）
        if any(f in missing_fields for f in ["management", "custodian", "found_date", "benchmark", "m_fee", "c_fee", "s_fee", "p_fee", "r_fee"]):
            try:
                basic_df = await asyncio.to_thread(tushare.get_fund_basic)
                if not basic_df.empty:
                    fund_row = None
                    for cand in candidates:
                        matched = basic_df[basic_df['ts_code'] == cand]
                        if not matched.empty:
                            fund_row = matched
                            break
                    if fund_row is None:
                        for cand in candidates:
                            matched = basic_df[basic_df['ts_code'].str.startswith(cand, na=False)]
                            if not matched.empty:
                                fund_row = matched
                                break

                    if fund_row is not None and not fund_row.empty:
                        row = fund_row.iloc[0]
                        b = result.setdefault("basic", {})
                        for key in ["management", "custodian", "found_date", "benchmark", "m_fee", "c_fee", "s_fee", "p_fee", "r_fee"]:
                            if key in missing_fields and not b.get(key):
                                b[key] = row.get(key)
                        # 补充名称等信息
                        if not b.get("name"):
                            b["name"] = row.get("name")
                        if not b.get("fund_type"):
                            b["fund_type"] = row.get("fund_type")
            except Exception as e:
                logger.warning(f"⚠️ [Tushare] 补充基础信息失败: {e}")

        # 2. 最新规模
        if "latest_share" in missing_fields:
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
                    latest_share = share_df.iloc[0]
                    result["latest_share"] = {
                        "trade_date": latest_share.get("trade_date") or latest_share.get("ann_date"),
                        "fd_share": latest_share.get("fd_share") or latest_share.get("share"),
                        "fd_amount": latest_share.get("fd_amount") or latest_share.get("amount"),
                    }
            except Exception as e:
                logger.warning(f"⚠️ [Tushare] 补充份额失败: {e}")

        # 3. 基金经理
        if "managers" in missing_fields:
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
                logger.warning(f"⚠️ [Tushare] 补充基金经理失败: {e}")

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
