"""
基金数据适配器
- 搜索：优先 AKShare fund_name_em（免费、无需Token），带Redis缓存
- 详情：优先 AKShare fund_info_ths（同花顺，字段完整），带Redis缓存1小时
  + fund_individual_basic_info_xq（雪球，补充规模、基金经理、评级等）
  + 指数型基金额外调用 fund_info_index_em
  + Tushare 仅作为最后补充（有频率限制）
"""
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd

logger = logging.getLogger("app.services.fund_data_adapter")

# 缓存配置
FUND_DETAIL_CACHE_TTL = 3600       # 基金详情缓存1小时
FUND_SEARCH_CACHE_TTL = 300        # 搜索结果缓存5分钟
FUND_NOT_FOUND_CACHE_TTL = 300     # 基金不存在缓存5分钟（防穿透）
FUND_DETAIL_CACHE_KEY = "fund:detail:{ts_code}"
FUND_SEARCH_CACHE_KEY = "fund:search:{keyword}:{market}:{limit}"
FUND_NOT_FOUND_KEY = "fund:notfound:{ts_code}"


class FundDataAdapter:
    """基金数据适配器（含Redis缓存）"""

    def __init__(self):
        self._tushare = None
        self._akshare_available = False
        self._ak = None
        self._redis = None
        self._redis_initialized = False
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

    def _get_redis(self):
        """延迟获取 Redis 客户端（在应用启动后才可用），支持重试"""
        if self._redis is not None:
            return self._redis
        try:
            # 优先尝试从 redis_client 获取已初始化的连接
            from app.core.redis_client import get_redis
            self._redis = get_redis()
            logger.info("✅ [FundDataAdapter] Redis 连接成功 (from redis_client)")
        except Exception as e:
            # 回退：使用环境变量自己创建连接（避免 keepalive 兼容性问题）
            logger.debug(f"[FundDataAdapter] get_redis 失败，尝试自建连接: {e}")
            try:
                import redis.asyncio as redis
                import os
                host = os.getenv("REDIS_HOST", "localhost")
                port = int(os.getenv("REDIS_PORT", "6379"))
                password = os.getenv("REDIS_PASSWORD", "")
                db = int(os.getenv("REDIS_DB", "0"))
                url = f"redis://:{password}@{host}:{port}/{db}" if password else f"redis://{host}:{port}/{db}"
                self._redis = redis.from_url(url, decode_responses=True)
                logger.info("✅ [FundDataAdapter] Redis 连接成功 (自建连接)")
            except Exception as e2:
                self._redis = None
                logger.warning(f"⚠️ [FundDataAdapter] Redis 自建连接也失败: {e2}")
        return self._redis

    def _get_tushare(self):
        """获取 Tushare provider（延迟加载）"""
        if self._tushare is None:
            from tradingagents.dataflows.providers.china.tushare import get_tushare_provider
            self._tushare = get_tushare_provider()
        return self._tushare

    # ==================== Redis 缓存辅助方法 ====================

    async def _get_cache(self, key: str) -> Optional[Any]:
        """从Redis获取缓存"""
        r = self._get_redis()
        if not r:
            return None
        try:
            data = await r.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.debug(f"[FundDataAdapter] Redis get cache failed: {e}")
        return None

    async def _set_cache(self, key: str, value: Any, ttl: int):
        """写入Redis缓存"""
        r = self._get_redis()
        if not r:
            return
        try:
            json_str = json.dumps(value, ensure_ascii=False, default=str)
            await r.setex(key, ttl, json_str)
        except Exception as e:
            logger.debug(f"[FundDataAdapter] Redis set cache failed: {e}")

    async def _delete_cache(self, key: str):
        """删除Redis缓存"""
        r = self._get_redis()
        if not r:
            return
        try:
            await r.delete(key)
        except Exception as e:
            logger.debug(f"[FundDataAdapter] Redis delete cache failed: {e}")

    # ==================== 搜索基金 ====================

    async def search_funds(self, keyword: str, market: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索基金：优先 AKShare fund_name_em，降级 Tushare；带Redis缓存"""
        cache_key = FUND_SEARCH_CACHE_KEY.format(keyword=keyword.lower(), market=market or "all", limit=limit)

        # 1. 查缓存
        cached = await self._get_cache(cache_key)
        if cached is not None:
            logger.info(f"💾 [FundDataAdapter] 搜索结果命中缓存: {keyword}")
            return cached

        # 2. 调用数据源
        result = []
        if self._akshare_available:
            try:
                logger.info(f"🔄 [FundDataAdapter] 尝试使用 AKShare 搜索基金: {keyword}")
                result = await self._search_with_akshare(keyword, limit)
                if result:
                    logger.info(f"✅ [FundDataAdapter] AKShare 搜索成功，找到 {len(result)} 只基金")
            except Exception as e:
                logger.warning(f"⚠️ [FundDataAdapter] AKShare 搜索失败: {e}，尝试 Tushare")

        if not result:
            try:
                logger.info(f"🔄 [FundDataAdapter] 使用 Tushare 搜索基金: {keyword}")
                result = await self._search_with_tushare(keyword, market, limit)
            except Exception as e:
                logger.error(f"❌ [FundDataAdapter] Tushare 搜索也失败: {e}")

        # 3. 写缓存
        if result:
            await self._set_cache(cache_key, result, FUND_SEARCH_CACHE_TTL)

        return result

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
        获取基金详情（带Redis缓存，TTL=1小时）
        1. 优先查Redis缓存
        2. 无缓存时：AKShare获取 → Tushare补充 → 写入Redis
        """
        cache_key = FUND_DETAIL_CACHE_KEY.format(ts_code=ts_code)
        notfound_key = FUND_NOT_FOUND_KEY.format(ts_code=ts_code)

        # 1. 检查是否标记为"不存在"（防缓存穿透）
        notfound = await self._get_cache(notfound_key)
        if notfound:
            logger.info(f"💾 [FundDataAdapter] 基金 {ts_code} 被标记为不存在，跳过查询")
            return {
                "ts_code": ts_code,
                "basic": {},
                "latest_nav": None,
                "latest_share": None,
                "managers": [],
                "nav_history": [],
                "_cached": True,
                "_not_found": True,
            }

        # 2. 查Redis缓存
        cached = await self._get_cache(cache_key)
        if cached is not None:
            logger.info(f"💾 [FundDataAdapter] 基金详情命中缓存: {ts_code}")
            cached["_cached"] = True
            cached["_cached_at"] = cached.get("_cached_at")
            return cached

        # 3. 无缓存，调用数据源
        result = {
            "ts_code": ts_code,
            "basic": {},
            "latest_nav": None,
            "latest_share": None,
            "managers": [],
            "nav_history": [],
            "_cached": False,
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

            # 获取历史净值（独立于详情获取，失败不影响其他数据）
            try:
                logger.info(f"🔄 [FundDataAdapter] 使用 AKShare 获取历史净值: {ts_code}")
                nav_history = await self._get_nav_history_with_akshare(ts_code)
                if nav_history:
                    result["nav_history"] = nav_history
                    logger.info(f"✅ [FundDataAdapter] 历史净值获取成功: {ts_code}，共 {len(nav_history)} 条")
            except Exception as e:
                logger.warning(f"⚠️ [FundDataAdapter] AKShare 获取历史净值失败: {e}")

            # 补充最新净值（场内 ETF/LOF 用 fund_etf_spot_em，或从 nav_history 提取）
            try:
                await self._get_latest_nav_with_akshare(ts_code, result)
            except Exception as e:
                logger.warning(f"⚠️ [FundDataAdapter] 补充最新净值失败: {e}")

        # 第2步：检查缺失字段，用 Tushare 补充
        missing_fields = self._check_missing_fields(result)
        if missing_fields:
            logger.info(f"🔄 [FundDataAdapter] AKShare 缺失字段 {missing_fields}，尝试用 Tushare 补充: {ts_code}")
            try:
                await self._fill_missing_with_tushare(ts_code, result, missing_fields)
                logger.info(f"✅ [FundDataAdapter] Tushare 补充完成: {ts_code}")
            except Exception as e:
                logger.warning(f"⚠️ [FundDataAdapter] Tushare 补充失败: {e}")

        # 4. 写入Redis缓存
        has_basic = bool(result.get("basic") and result["basic"].get("name"))
        has_nav = bool(result.get("latest_nav") or result.get("nav_history"))

        if has_basic or has_nav:
            # 有数据才缓存，并记录缓存时间
            result_to_cache = {**result, "_cached_at": datetime.now().isoformat()}
            # 移除内部标记字段
            result_to_cache.pop("_cached", None)
            await self._set_cache(cache_key, result_to_cache, FUND_DETAIL_CACHE_TTL)
            logger.info(f"💾 [FundDataAdapter] 基金详情已缓存: {ts_code} (TTL={FUND_DETAIL_CACHE_TTL}s)")
        else:
            # 完全没有数据，标记为不存在（防穿透）
            await self._set_cache(notfound_key, {"ts_code": ts_code, "time": datetime.now().isoformat()}, FUND_NOT_FOUND_CACHE_TTL)
            logger.warning(f"⚠️ [FundDataAdapter] 基金 {ts_code} 无任何数据，标记为不存在")

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

        # ========== 5. 基金经理详细信息 fund_manager_em ==========
        if result.get("managers"):
            try:
                logger.info(f"🔄 [AKShare] 调用 fund_manager_em 补充基金经理详情")
                mgr_df = self._ak.fund_manager_em()
                if mgr_df is not None and not mgr_df.empty:
                    # 动态查找列名
                    name_col = self._find_col(mgr_df, ['姓名', 'name', '基金经理'])
                    company_col = self._find_col(mgr_df, ['所属公司', '基金公司', 'company'])
                    tenure_col = self._find_col(mgr_df, ['累计任职时间', '任职时间', 'tenure'])
                    start_col = self._find_col(mgr_df, ['任职起始日期', '起始日期', 'begin_date'])
                    current_funds_col = self._find_col(mgr_df, ['现任基金', '在管基金', 'current_funds'])
                    resume_col = self._find_col(mgr_df, ['基金经理简介', '简介', 'resume'])

                    if name_col:
                        for i, mgr in enumerate(result["managers"]):
                            mgr_name = mgr.get("name", "")
                            if not mgr_name:
                                continue

                            # 按姓名匹配
                            matched = mgr_df[mgr_df[name_col].astype(str).str.strip() == mgr_name]
                            if matched.empty:
                                continue

                            row = matched.iloc[0]

                            # 补充详细信息
                            if company_col:
                                val = row.get(company_col)
                                if val is not None and pd.notna(val):
                                    mgr["company"] = str(val).strip()

                            if tenure_col:
                                val = row.get(tenure_col)
                                if val is not None and pd.notna(val):
                                    mgr["tenure"] = str(val).strip()

                            if start_col:
                                val = row.get(start_col)
                                if val is not None and pd.notna(val):
                                    mgr["start_date"] = str(val).strip()

                            if current_funds_col:
                                val = row.get(current_funds_col)
                                if val is not None and pd.notna(val):
                                    mgr["current_funds"] = str(val).strip()

                            if resume_col:
                                val = row.get(resume_col)
                                if val is not None and pd.notna(val):
                                    mgr["resume"] = str(val).strip()

                            # 更新回列表
                            result["managers"][i] = mgr

                        logger.info(f"✅ [AKShare] fund_manager_em 补充完成，共 {len(result['managers'])} 位基金经理")
            except Exception as e:
                logger.warning(f"⚠️ [AKShare] fund_manager_em 获取失败: {e}")

        return has_basic

    async def _get_nav_history_with_akshare(self, ts_code: str, limit: int = 30) -> List[Dict[str, Any]]:
        """使用 AKShare 获取基金历史净值数据

        接口优先级：
        1. fund_open_fund_info_em: 开放式基金历史净值（最通用，返回单位净值+累计净值+日增长率）
        2. fund_etf_hist_em: ETF 历史行情
        3. fund_lof_hist_em: LOF 历史行情
        """
        pure_code = ts_code.split('.')[0] if '.' in ts_code else ts_code
        nav_history = []

        # ========== 1. 优先尝试 fund_open_fund_info_em（最通用）==========
        try:
            logger.info(f"🔄 [AKShare] 调用 fund_open_fund_info_em: {pure_code}")
            # indicator="单位净值走势" 返回 DataFrame，通常含日期+净值
            nav_df = self._ak.fund_open_fund_info_em(symbol=pure_code, indicator="单位净值走势")
            if nav_df is not None and not nav_df.empty:
                logger.info(f"[AKShare] fund_open_fund_info_em 返回 {len(nav_df)} 条")
                # 列名固定为：净值日期, 单位净值, 日增长率（部分接口还有累计净值）
                # 使用精确列名，避免 _find_col 的模糊匹配问题
                date_col = '净值日期' if '净值日期' in nav_df.columns else None
                nav_col = '单位净值' if '单位净值' in nav_df.columns else None
                acc_nav_col = '累计净值' if '累计净值' in nav_df.columns else None
                daily_return_col = '日增长率' if '日增长率' in nav_df.columns else None

                # 如果精确列名找不到，再用 _find_col 兜底
                if date_col is None:
                    date_col = self._find_col(nav_df, ['净值日期', 'x', '日期', 'date'])
                if nav_col is None:
                    nav_col = self._find_col(nav_df, ['单位净值', 'y'])

                if date_col and nav_col:
                    for _, row in nav_df.tail(limit).iterrows():
                        date_val = row.get(date_col)
                        nav_val = row.get(nav_col)
                        if pd.notna(date_val) and pd.notna(nav_val):
                            # 确保 nav_val 是数值类型
                            try:
                                nav_float = float(nav_val)
                            except (ValueError, TypeError):
                                continue
                            item = {
                                "nav_date": str(date_val).strip(),
                                "nav": nav_float,
                            }
                            if acc_nav_col:
                                acc_val = row.get(acc_nav_col)
                                if pd.notna(acc_val):
                                    try:
                                        item["acc_nav"] = float(acc_val)
                                    except (ValueError, TypeError):
                                        pass
                            if daily_return_col:
                                ret_val = row.get(daily_return_col)
                                if pd.notna(ret_val):
                                    # 日增长率可能是百分数字符串或小数
                                    try:
                                        ret_str = str(ret_val).strip().replace('%', '')
                                        item["daily_return"] = float(ret_str) / 100
                                    except (ValueError, TypeError):
                                        item["daily_return"] = None
                            nav_history.append(item)

                    if nav_history:
                        # 按日期倒序（最新的在前面）
                        nav_history.reverse()
                        logger.info(f"✅ [AKShare] fund_open_fund_info_em 成功获取 {len(nav_history)} 条净值")
                        return nav_history
            else:
                logger.warning(f"⚠️ [AKShare] fund_open_fund_info_em 返回空数据: {pure_code}")
        except Exception as e:
            logger.warning(f"⚠️ [AKShare] fund_open_fund_info_em 失败: {e}")

        # ========== 2. 尝试 fund_etf_hist_em（ETF）==========
        try:
            logger.info(f"🔄 [AKShare] 调用 fund_etf_hist_em: {pure_code}")
            etf_df = self._ak.fund_etf_hist_em(symbol=pure_code, period="daily", adjust="qfq")
            if etf_df is not None and not etf_df.empty:
                logger.info(f"[AKShare] fund_etf_hist_em 返回 {len(etf_df)} 条")
                # 列名通常是 日期, 开盘, 收盘, 最高, 最低, 成交量
                date_col = self._find_col(etf_df, ['日期', 'date'])
                close_col = self._find_col(etf_df, ['收盘', 'close', '收盘价'])
                if date_col and close_col:
                    for _, row in etf_df.tail(limit).iterrows():
                        date_val = row.get(date_col)
                        close_val = row.get(close_col)
                        if pd.notna(date_val) and pd.notna(close_val):
                            try:
                                nav_history.append({
                                    "nav_date": str(date_val).strip(),
                                    "nav": float(close_val),
                                })
                            except (ValueError, TypeError):
                                continue
                    if nav_history:
                        nav_history.reverse()
                        logger.info(f"✅ [AKShare] fund_etf_hist_em 成功获取 {len(nav_history)} 条净值")
                        return nav_history
            else:
                logger.warning(f"⚠️ [AKShare] fund_etf_hist_em 返回空数据: {pure_code}")
        except Exception as e:
            logger.warning(f"⚠️ [AKShare] fund_etf_hist_em 失败: {e}")

        # ========== 3. 尝试 fund_lof_hist_em（LOF）==========
        try:
            logger.info(f"🔄 [AKShare] 调用 fund_lof_hist_em: {pure_code}")
            lof_df = self._ak.fund_lof_hist_em(symbol=pure_code, period="daily", adjust="qfq")
            if lof_df is not None and not lof_df.empty:
                logger.info(f"[AKShare] fund_lof_hist_em 返回 {len(lof_df)} 条")
                date_col = self._find_col(lof_df, ['日期', 'date'])
                close_col = self._find_col(lof_df, ['收盘', 'close', '收盘价'])
                if date_col and close_col:
                    for _, row in lof_df.tail(limit).iterrows():
                        date_val = row.get(date_col)
                        close_val = row.get(close_col)
                        if pd.notna(date_val) and pd.notna(close_val):
                            try:
                                nav_history.append({
                                    "nav_date": str(date_val).strip(),
                                    "nav": float(close_val),
                                })
                            except (ValueError, TypeError):
                                continue
                    if nav_history:
                        nav_history.reverse()
                        logger.info(f"✅ [AKShare] fund_lof_hist_em 成功获取 {len(nav_history)} 条净值")
                        return nav_history
            else:
                logger.warning(f"⚠️ [AKShare] fund_lof_hist_em 返回空数据: {pure_code}")
        except Exception as e:
            logger.warning(f"⚠️ [AKShare] fund_lof_hist_em 失败: {e}")

        # ========== 4. 兜底：fund_name_em 只有最新一条 ==========
        if not nav_history:
            logger.warning(f"⚠️ [AKShare] 所有历史净值接口均失败: {pure_code}")

        return nav_history

    async def _get_latest_nav_with_akshare(self, ts_code: str, result: Dict[str, Any]):
        """使用 AKShare 获取基金最新净值（场内 ETF/LOF 用 fund_etf_spot_em）"""
        pure_code = ts_code.split('.')[0] if '.' in ts_code else ts_code
        fund_type = (result.get("basic") or {}).get("fund_type", "")

        # 优先从 nav_history 补充 latest_nav
        nav_history = result.get("nav_history", [])
        if nav_history and not result.get("latest_nav"):
            latest = nav_history[0]  # nav_history 已经是倒序，第一条是最新的
            result["latest_nav"] = {
                "nav_date": latest.get("nav_date"),
                "nav": latest.get("nav"),
                "acc_nav": latest.get("acc_nav"),
                "daily_return": latest.get("daily_return"),
            }
            logger.info(f"✅ [AKShare] 从 nav_history 补充 latest_nav: {latest.get('nav_date')} = {latest.get('nav')}")
            return

        # 对于场内 ETF/LOF，尝试 fund_etf_spot_em 获取实时价格
        if "ETF" in str(fund_type) or "LOF" in str(fund_type):
            try:
                logger.info(f"🔄 [AKShare] 调用 fund_etf_spot_em 获取最新价格: {pure_code}")
                spot_df = self._ak.fund_etf_spot_em()
                if spot_df is not None and not spot_df.empty:
                    code_col = self._find_col(spot_df, ['代码', 'code'])
                    if code_col:
                        matched = spot_df[spot_df[code_col].astype(str).str.strip() == pure_code]
                        if not matched.empty:
                            row = matched.iloc[0]
                            price_col = self._find_col(spot_df, ['最新价', 'price', 'close'])
                            change_col = self._find_col(spot_df, ['涨跌幅', 'change_pct'])
                            date_col = self._find_col(spot_df, ['数据日期', 'date'])

                            result["latest_nav"] = {
                                "nav_date": str(row.get(date_col)).strip() if date_col and pd.notna(row.get(date_col)) else None,
                                "nav": float(row.get(price_col)) if price_col and pd.notna(row.get(price_col)) else None,
                                "daily_return": float(row.get(change_col)) / 100 if change_col and pd.notna(row.get(change_col)) else None,
                            }
                            logger.info(f"✅ [AKShare] fund_etf_spot_em 获取成功: {pure_code} = {result['latest_nav']['nav']}")
            except Exception as e:
                logger.warning(f"⚠️ [AKShare] fund_etf_spot_em 失败: {e}")

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
