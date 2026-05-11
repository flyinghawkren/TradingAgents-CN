"""
基金分析服务
基于Tushare基金数据，提供基金综合分析功能
"""

import asyncio
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.core.database import get_mongo_db
from app.models.analysis import (
    FundAnalysisRequest, FundAnalysisResult, FundInfo,
    AnalysisStatus, AnalysisParameters
)
from tradingagents.dataflows.providers.china.tushare import get_tushare_provider
from app.services.model_capability_service import get_model_capability_service
from tradingagents.llm_clients.provider_keys import normalize_provider_key

logger = logging.getLogger("app.services.fund_analysis_service")


class FundAnalysisService:
    """基金分析服务"""

    def __init__(self):
        self.tushare = get_tushare_provider()

    async def get_fund_info(self, ts_code: str) -> Optional[FundInfo]:
        """获取基金基础信息"""
        try:
            # 在线程池中执行同步Tushare调用
            df = await asyncio.to_thread(self.tushare.get_fund_basic)
            if df.empty:
                return None

            fund_row = df[df['ts_code'] == ts_code]
            if fund_row.empty:
                return None

            row = fund_row.iloc[0]
            return FundInfo(
                ts_code=ts_code,
                name=row.get('name', ''),
                short_name=row.get('short_name'),
                fund_type=row.get('fund_type'),
                market=row.get('market'),
                status=row.get('status'),
                found_date=row.get('found_date'),
                list_date=row.get('list_date'),
                invest_type=row.get('invest_type'),
                type=row.get('type'),
                management=row.get('management'),
                custodian=row.get('custodian'),
                benchmark=row.get('benchmark')
            )
        except Exception as e:
            logger.error(f"❌ 获取基金基础信息失败: {ts_code} - {e}")
            return None

    async def get_fund_comprehensive_data(self, ts_code: str) -> Dict[str, Any]:
        """获取基金综合数据"""
        try:
            data = await asyncio.to_thread(self.tushare.get_fund_comprehensive, ts_code)
            return data
        except Exception as e:
            logger.error(f"❌ 获取基金综合数据失败: {ts_code} - {e}")
            return {}

    async def analyze_fund(self, request: FundAnalysisRequest) -> FundAnalysisResult:
        """
        执行基金综合分析

        分析维度：
        1. 净值走势与业绩表现
        2. 持仓结构与集中度
        3. 基金经理能力评估
        4. 风险收益特征
        5. 综合投资建议
        """
        ts_code = request.ts_code
        logger.info(f"🚀 开始基金分析: {ts_code}")

        start_time = datetime.now()

        # 获取基金数据
        fund_data = await self.get_fund_comprehensive_data(ts_code)
        fund_info = await self.get_fund_info(ts_code)

        if not fund_info:
            return FundAnalysisResult(
                ts_code=ts_code,
                error_message="未找到基金信息，请检查基金代码是否正确"
            )

        # 构建分析提示词
        prompt = self._build_fund_analysis_prompt(ts_code, fund_info, fund_data)

        # 调用大模型进行分析
        try:
            report_text = await self._call_llm_for_analysis(prompt, request.parameters)

            # 解析报告
            result = self._parse_fund_report(ts_code, fund_info, report_text)
            result.execution_time = (datetime.now() - start_time).total_seconds()

            logger.info(f"✅ 基金分析完成: {ts_code}")
            return result

        except Exception as e:
            logger.error(f"❌ 基金分析失败: {ts_code} - {e}")
            return FundAnalysisResult(
                ts_code=ts_code,
                fund_name=fund_info.name,
                error_message=f"分析失败: {str(e)}"
            )

    def _build_fund_analysis_prompt(self, ts_code: str, fund_info: FundInfo,
                                    fund_data: Dict[str, Any]) -> str:
        """构建基金分析提示词"""

        # 基础信息
        basic_section = f"""
## 基金基础信息
- 基金代码: {ts_code}
- 基金名称: {fund_info.name}
- 基金类型: {fund_info.fund_type or '未知'}
- 投资类型: {fund_info.invest_type or '未知'}
- 成立日期: {fund_info.found_date or '未知'}
- 上市日期: {fund_info.list_date or '未知'}
- 管理人: {fund_info.management or '未知'}
- 托管人: {fund_info.custodian or '未知'}
- 业绩基准: {fund_info.benchmark or '未知'}
"""

        # 净值数据
        nav_section = ""
        nav_df = fund_data.get('nav_history')
        if nav_df is not None and not nav_df.empty:
            latest_nav = nav_df.iloc[0]
            nav_section = f"""
## 最新净值数据
- 净值日期: {latest_nav.get('nav_date', '未知')}
- 单位净值: {latest_nav.get('unit_nav', '未知')}
- 累计净值: {latest_nav.get('accum_nav', '未知')}
- 近期净值走势: {'上涨' if len(nav_df) > 1 and nav_df.iloc[0].get('unit_nav', 0) > nav_df.iloc[-1].get('unit_nav', 0) else '下跌'}
"""

        # 持仓数据
        portfolio_section = ""
        portfolio_df = fund_data.get('portfolio')
        if portfolio_df is not None and not portfolio_df.empty:
            top_holdings = portfolio_df.head(10)
            holdings_text = "\n".join([
                f"  - {row.get('symbol', '')}: {row.get('name', '')} (占比: {row.get('mkv', '未知')})"
                for _, row in top_holdings.iterrows()
            ])
            portfolio_section = f"""
## 前十大持仓
{holdings_text}
- 持仓集中度: {'集中' if len(portfolio_df) < 20 else '分散'}
"""

        # 基金经理
        manager_section = ""
        manager_df = fund_data.get('manager')
        if manager_df is not None and not manager_df.empty:
            manager = manager_df.iloc[0]
            manager_section = f"""
## 基金经理信息
- 姓名: {manager.get('name', '未知')}
- 性别: {manager.get('gender', '未知')}
- 任职日期: {manager.get('begin_date', '未知')}
- 管理规模: {manager.get('m_fee', '未知')}
"""

        user_prompt = f"""# 基金分析报告请求

{basic_section}
{nav_section}
{portfolio_section}
{manager_section}

## 分析要求
请作为资深基金分析师，基于以上数据完成以下分析并输出结构化报告：

### 1. 基金概况与定位
- 基金类型特点及适合的投资者群体
- 与同类基金的差异化定位

### 2. 业绩表现评估
- 净值走势分析（短期/中期趋势）
- 与业绩基准的对比评估

### 3. 持仓结构分析
- 行业/板块分布是否合理
- 持仓集中度风险评估
- 重仓股质量评估

### 4. 基金经理评价
- 管理能力与经验评估
- 投资风格稳定性
- 历史业绩参考

### 5. 风险评估
- 市场风险、流动性风险、集中度风险
- 适合的风险承受能力等级

### 6. 投资建议（重点）
- 是否值得买入/持有/卖出
- 建议配置比例
- 关注要点与择时建议

请用中文输出，结构清晰，建议具体可操作。"""

        return user_prompt

    async def _call_llm_for_analysis(self, prompt: str,
                                     parameters: Optional[AnalysisParameters] = None) -> str:
        """调用大模型进行基金分析"""
        from tradingagents.llm_clients import create_llm_client
        from langchain_core.messages import SystemMessage, HumanMessage

        system_prompt = """你是一位资深基金分析师，擅长从多维度分析公募基金，并给出专业的投资建议。
请基于提供的基金数据，进行客观、全面的分析。"""

        # 获取模型配置
        research_depth = parameters.research_depth if parameters else "标准"
        capability_service = get_model_capability_service()
        _, deep_model = capability_service.recommend_models_for_depth(research_depth)

        # 获取模型供应商信息
        from app.services.simple_analysis_service import get_provider_and_url_by_model_sync
        provider_info = get_provider_and_url_by_model_sync(deep_model)
        provider = provider_info["provider"]
        backend_url = provider_info["backend_url"]
        api_key = provider_info["api_key"]

        provider_key = normalize_provider_key(provider)
        llm_client = create_llm_client(
            provider=provider_key,
            model=deep_model,
            base_url=backend_url,
            api_key=api_key,
            temperature=0.3,
            max_tokens=8000,
        )

        llm = llm_client.get_llm()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt),
        ]

        # 在线程池中执行
        response = await asyncio.to_thread(llm.invoke, messages)
        return response.content if hasattr(response, "content") else str(response)

    def _parse_fund_report(self, ts_code: str, fund_info: FundInfo,
                           report_text: str) -> FundAnalysisResult:
        """解析基金分析报告"""
        return FundAnalysisResult(
            ts_code=ts_code,
            fund_name=fund_info.name,
            fund_type=fund_info.fund_type,
            comprehensive_report=report_text,
            summary=report_text[:500] if report_text else "",
            recommendation="请查看完整分析报告",
            key_points=["基金分析已完成，请查看详细报告"]
        )


# 全局服务实例
_fund_analysis_service = None


def get_fund_analysis_service() -> FundAnalysisService:
    """获取全局基金分析服务实例"""
    global _fund_analysis_service
    if _fund_analysis_service is None:
        _fund_analysis_service = FundAnalysisService()
    return _fund_analysis_service
