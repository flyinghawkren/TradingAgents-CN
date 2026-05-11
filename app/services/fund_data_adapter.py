"""
基金数据适配器
- 搜索：优先 AKShare fund_name_em（免费、无需Token）
- 详情：优先 AKShare fund_info_ths（同花顺，字段完整）
  + fund_individual_basic_info_xq（雪球，补充规模、基金经理、评级等）
  + 指数型基金额外调用 fund_info_index_em
  + Tushare 仅作为最后补充（有频率限制）
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
        """搜索基金：优先 AKShare fund_name_em，降级 Tushare"""
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
        """使用 AKShare fund_name_em 搜索基金"""
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
           - fund_info_ths: 同花顺基金详情（费率、管理人、托管人、业绩基准等）
           - fund_individual_basic_info_xq: 雪球基金详情（规模、基金经理、评级等）
           - fund_info_index_em: 指数型基金额外信息（跟踪标的、跟踪方式等）
           - fund_name_em: 最新净值
        2. Tushare 仅补充缺失字段（有频率限制）
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

        # ========== 1. 同花顺基金基本信息 fund_info_ths（核心数据源）==========
        try:
            logger.info(f"🔄 [AKShare] 调用 fund_info_ths: {pure_code}")
            ths_df = self._ak.fund_info_ths(symbol=pure_code)
            if ths_df is not None and not ths_df.empty:
                # fund_info_ths 返回的是 item/value 两列格式
                # 转换为字典
                ths_dict = {}
                for _, row in ths_df.iterrows():
                    item = str(row.get("字段", row.get("item", ""))).strip()
                    value = row.get("值", row.get("value", ""))
                    if item:
                        ths_dict[item] = value

                logger.info(f"[AKShare] fund_info_ths 返回字段: {list(ths_dict.keys())}")

                if ths_dict:
                    has_basic = True
                    result["basic"] = {
                        "ts_code": ts_code,
                        "name": self._extract_value(ths_dict, ["基金简称", "简称", "name"]),
                        "fund_type": self._extract_value(ths_dict, ["基金类型", "类型", "fund_type"]),
                        "invest_type": self._extract_value(ths_dict, ["投资类型", "invest_type"]),
                        "management": self._extract_value(ths_dict, ["基金管理人", "管理人", "基金公司", "management"]),
                        "custodian": self._extract_value(ths_dict, ["基金托管人", "托管人", "托管银行", "custodian"]),
                        "found_date": self._extract_value(ths_dict, ["成立日期", "成立日", "found_date"]),
                        "benchmark": self._extract_value(ths_dict, ["业绩比较基准", "业绩基准", "比较基准", "benchmark"]),
                        "m_fee": self._parse_fee(ths_dict, ["管理费", "管理费率", "m_fee"]),
                        "c_fee": self._parse_fee(ths_dict, ["托管费", "托管费率", "c_fee"]),
                        "p_fee": self._parse_fee(ths_dict, ["最高申购费", "申购费率", "最高认购费", "p_fee"]),
                        "r_fee": self._parse_fee(ths_dict, ["最高赎回费", "赎回费率", "r_fee"]),
                        "market": "O",
                        "status": "L",
                    }

                    # 基金经理（同花顺返回的是字符串，可能多个）
                    mgr_names = self._extract_value(ths_dict, ["基金经理", "经理人", "manager"])
                    if mgr_names:
                        # 可能返回 "伍臣东" 或 "王泽实 万方方"
                        for name in str(mgr_names).split():
                            name = name.strip()
                            if name and name not in [m.get("name") for m in result["managers"]]:
                                result["managers"].append({"name": name})

                    # 规模（同花顺返回格式如 "4.13亿份（2026-03-31）"）
                    scale_str = self._extract_value(ths_dict, ["份额规模", "规模", "最新规模", "fund_size"])
                    if scale_str:
                        parsed = self._parse_scale(str(scale_str))
                        if parsed:
                            result["latest_share"] = parsed

                    # 成立规模
                    init_scale = self._extract_value(ths_dict, ["成立规模", "初始规模", "init_scale"])
                    if init_scale and not result.get("latest_share"):
                        parsed = self._parse_scale(str(init_scale))
                        if parsed:
                            result["latest_share"] = parsed
            else:
                logger.warning(f"⚠️ [AKShare] fund_info_ths 返回空数据: {pure_code}")
        except Exception as e:
            logger.warning(f"⚠️ [AKShare] fund_info_ths 获取失败: {e}")

        # ========== 2. 雪球基金详情 fund_individual_basic_info_xq（补充数据源）==========
        try:
            logger.info(f"🔄 [AKShare] 调用 fund_individual_basic_info_xq: {pure_code}")
            xq_df = self._ak.fund_individual_basic_info_xq(symbol=pure_code)
            if xq_df is not None and not xq_df.empty:
                xq_dict = {}
                for _, row in xq_df.iterrows():
                    item = str(row.get("item", row.get("字段", ""))).strip()
                    value = row.get("value", row.get("值", ""))
                    if item:
                        xq_dict[item] = value

                logger.info(f"[AKShare] fund_individual_basic_info_xq 返回字段: {list(xq_dict.keys())}")

                # 确保 basic 存在
                if not result.get("basic"):
                    result["basic"] = {"ts_code": ts_code, "market": "O", "status": "L"}
                    has_basic = True
                b = result["basic"]

                # 补充缺失字段
                if not b.get("name"):
                    b["name"] = self._extract_value(xq_dict, ["基金名称", "名称", "name"])
                if not b.get("fund_type"):
                    b["fund_type"] = self._extract_value(xq_dict, ["基金类型", "类型", "fund_type"])
                if not b.get("management"):
                    b["management"] = self._extract_value(xq_dict, ["基金公司", "管理人", "management"])
                if not b.get("custodian"):
                    b["custodian"] = self._extract_value(xq_dict, ["托管银行", "托管人", "custodian"])
                if not b.get("found_date"):
                    b["found_date"] = self._extract_value(xq_dict, ["成立时间", "成立日期", "found_date"])
                if not b.get("benchmark"):
                    b["benchmark"] = self._extract_value(xq_dict, ["业绩比较基准", "业绩基准", "benchmark"])

                # 规模（雪球格式如 "27.30亿"）
                if not result.get("latest_share"):
                    scale_str = self._extract_value(xq_dict, ["最新规模", "规模", "fund_size"])
                    if scale_str:
                        parsed = self._parse_scale(str(scale_str))
                        if parsed:
                            result["latest_share"] = parsed

                # 基金经理（雪球可能返回 "王泽实 万方方"）
                mgr_names = self._extract_value(xq_dict, ["基金经理", "经理人", "manager"])
                if mgr_names:
                    for name in str(mgr_names).split():
                        name = name.strip()
                        if name and name not in [m.get("name") for m in result["managers"]]:
                            result["managers"].append({"name": name})
            else:
                logger.warning(f"⚠️ [AKShare] fund_individual_basic_info_xq 返回空数据: {pure_code}")
        except Exception as e:
            logger.warning(f"⚠️ [AKShare] fund_individual_basic_info_xq 获取失败: {e}")

        # ========== 3. fund_name_em：最新净值 ==========
        try:
            df = self._ak.fund_name_em()
            if not df.empty:
                code_col = self._find_col(df, ['基金代码', 'code', '代码'])
                nav_col = self._find_col(df, ['单位净值', 'nav', '净值'])
                acc_nav_col = self._find_col(df, ['累计净值', 'acc_nav'])
                date_col = self._find_col(df, ['日期', 'date', 'nav_date'])
                daily_return_col = self._find_col(df, ['日增长率', '日涨幅', 'daily_return'])

                if code_col:
                    matched = df[df[code_col].astype(str).str.strip() == pure_code]
                    if not matched.empty:
                        row = matched.iloc[0]
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
            logger.warning(f"⚠️ [AKShare] fund_name_em 净值获取失败: {e}")

        # ========== 4. 指数型基金额外信息 fund_info_index_em ==========
        fund_type = (result.get("basic") or {}).get("fund_type", "")
        if fund_type and ("指数" in str(fund_type) or "ETF" in str(fund_type) or "LOF" in str(fund_type)):
            try:
                logger.info(f"🔄 [AKShare] 检测到指数型基金，调用 fund_info_index_em: {pure_code}")
                # fund_info_index_em 返回全量数据表，需要筛选
                idx_df = self._ak.fund_info_index_em(symbol="全部", indicator="全部")
                if idx_df is not None and not idx_df.empty:
                    code_col = self._find_col(idx_df, ['基金代码', 'code', '代码'])
                    if code_col:
                        matched = idx_df[idx_df[code_col].astype(str).str.strip() == pure_code]
                        if not matched.empty:
                            row = matched.iloc[0]
                            b = result.setdefault("basic", {})
                            # 跟踪标的
                            track_col = self._find_col(idx_df, ['跟踪标的', '跟踪指数', 'track_index'])
                            if track_col and not b.get("benchmark"):
                                b["benchmark"] = str(row.get(track_col, '')).strip() or None
                            # 跟踪方式
                            mode_col = self._find_col(idx_df, ['跟踪方式', 'track_mode'])
                            if mode_col:
                                b["track_mode"] = str(row.get(mode_col, '')).strip() or None
                            # 手续费
                            fee_col = self._find_col(idx_df, ['手续费', 'fee'])
                            if fee_col and not b.get("p_fee"):
                                try:
                                    b["p_fee"] = float(row.get(fee_col))
                                except (ValueError, TypeError):
                                    pass
            except Exception as e:
                logger.debug(f"[AKShare] fund_info_index_em 获取失败（非关键）: {e}")

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

    # ==================== 辅助方法 ====================

    @staticmethod
    def _find_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        """在 DataFrame 列中查找匹配的列名"""
        for col in df.columns:
            for cand in candidates:
                if cand in str(col):
                    return col
        return None

    @staticmethod
    def _extract_value(data_dict: Dict[str, Any], keys: List[str]) -> Optional[str]:
        """从字典中提取第一个匹配的值"""
        for key in keys:
            for k, v in data_dict.items():
                if key in str(k) and v is not None:
                    val = str(v).strip()
                    if val and val != "nan" and val != "None":
                        return val
        return None

    @staticmethod
    def _parse_fee(data_dict: Dict[str, Any], keys: List[str]) -> Optional[float]:
        """解析费率字段，去除 % 符号"""
        for key in keys:
            for k, v in data_dict.items():
                if key in str(k) and v is not None:
                    try:
                        val_str = str(v).strip().replace('%', '').replace('％', '')
                        if val_str and val_str != "nan" and val_str != "None":
                            return float(val_str)
                    except (ValueError, TypeError):
                        continue
        return None

    @staticmethod
    def _parse_scale(scale_str: str) -> Optional[Dict[str, Any]]:
        """解析规模字符串，如 '4.13亿份（2026-03-31）' 或 '27.30亿'"""
        try:
            import re
            # 提取数字
            num_match = re.search(r'(\d+\.?\d*)', str(scale_str))
            if not num_match:
                return None

            num = float(num_match.group(1))
            # 判断单位
            if '亿' in str(scale_str):
                num = num * 100000000
            elif '万' in str(scale_str):
                num = num * 10000

            # 提取日期
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', str(scale_str))
            trade_date = date_match.group(1) if date_match else None

            # 判断是份额还是金额
            if '份' in str(scale_str):
                return {"trade_date": trade_date, "fd_share": num, "fd_amount": None}
            else:
                return {"trade_date": trade_date, "fd_share": None, "fd_amount": num}
        except Exception:
            return None


# 全局适配器实例
_fund_data_adapter = None


def get_fund_data_adapter() -> FundDataAdapter:
    """获取全局基金数据适配器实例"""
    global _fund_data_adapter
    if _fund_data_adapter is None:
        _fund_data_adapter = FundDataAdapter()
    return _fund_data_adapter
