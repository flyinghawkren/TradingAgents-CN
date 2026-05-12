"""
基金分析任务服务
支持异步任务、进度跟踪、多分析师并行分析
"""
import asyncio
import uuid
import logging
import concurrent.futures
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from app.core.database import get_mongo_db
from app.models.analysis import FundAnalysisRequest, FundAnalysisResult, AnalysisStatus
from app.services.memory_state_manager import get_memory_state_manager, TaskStatus
from app.services.fund_data_adapter import get_fund_data_adapter
from app.services.simple_analysis_service import get_provider_and_url_by_model_sync
from app.services.model_capability_service import get_model_capability_service
from tradingagents.llm_clients.provider_keys import normalize_provider_key

logger = logging.getLogger("app.services.fund_analysis_task_service")

# 分析师配置
FUND_ANALYST_PROMPTS = {
    "净值分析师": {
        "role": "你是一位专业的基金净值分析师，擅长分析基金的净值走势、历史业绩、回撤控制和超额收益。",
        "focus": """
请重点分析以下内容：
1. 净值走势分析：短期（1个月）、中期（3-6个月）、长期（1年以上）趋势判断
2. 业绩评估：与业绩比较基准的对比，超额收益能力
3. 回撤控制：最大回撤、波动率分析
4. 风险调整后收益：夏普比率、卡玛比率等（如有数据）
5. 同类排名：在同类基金中的业绩分位（如有数据）
""",
    },
    "持仓分析师": {
        "role": "你是一位专业的基金持仓分析师，擅长分析基金的持仓结构、行业配置、重仓股质量和集中度风险。",
        "focus": """
请重点分析以下内容：
1. 持仓集中度：前十大重仓股/债券占比，集中度风险评估
2. 行业/板块分布：行业配置是否合理，是否存在过度集中
3. 重仓股质量：重仓标的质地、估值水平、成长潜力
4. 持仓风格：成长型/价值型/平衡型判断
5. 调仓频率：近期是否有重大调仓动作
""",
    },
    "基金经理评估师": {
        "role": "你是一位专业的基金经理评估师，擅长评估基金经理的投资能力、管理经验和稳定性。",
        "focus": """
请重点分析以下内容：
1. 管理经验：从业年限、管理该基金的时间
2. 投资风格：偏好大盘股/小盘股、成长/价值、行业偏好
3. 业绩稳定性：任期内的业绩一致性
4. 在管基金情况：管理基金数量、总规模
5. 综合评价：该基金经理的核心优势和潜在风险
""",
    },
    "风险评估师": {
        "role": "你是一位专业的基金风险评估师，擅长从多维度评估基金的风险特征。",
        "focus": """
请重点分析以下内容：
1. 市场风险：beta系数、市场敏感度
2. 流动性风险：基金规模、申赎便利性（场内/场外）
3. 集中度风险：持仓集中度、单一行业/个股占比
4. 信用风险：如涉及债券，评估信用风险暴露
5. 适合投资者类型：保守型/稳健型/积极型/激进型
""",
    },
    "费率分析师": {
        "role": "你是一位专业的基金费率分析师，擅长评估基金的综合费率和性价比。",
        "focus": """
请重点分析以下内容：
1. 综合费率水平：管理费+托管费+销售服务费+申购赎回费
2. 同类对比：与同类基金的费率对比
3. 费率性价比：费率水平是否与业绩表现匹配
4. C类/A类选择建议：如适用，给出份额选择建议
5. 长期持有成本：长期投资的费率累积影响
""",
    },
    "宏观分析师": {
        "role": "你是一位专业的宏观分析师，擅长分析宏观经济环境对基金表现的影响。",
        "focus": """
请重点分析以下内容：
1. 当前市场环境：股市/债市/商品市场的大环境判断
2. 政策影响：货币政策、财政政策对该基金的影响
3. 行业景气度：该基金重点配置行业的景气周期
4. 未来展望：未来6-12个月的市场预判对基金的影响
5. 配置时机建议：当前是否是配置该基金的好时机
""",
    },
}


class FundAnalysisTaskService:
    """基金分析任务服务"""

    def __init__(self):
        self.memory_manager = get_memory_state_manager()
        self._thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        self._progress_trackers: Dict[str, Any] = {}

        try:
            from app.services.websocket_manager import get_websocket_manager
            self.memory_manager.set_websocket_manager(get_websocket_manager())
        except ImportError:
            logger.warning("⚠️ WebSocket 管理器不可用")

    async def create_fund_analysis_task(
        self,
        user_id: str,
        request: FundAnalysisRequest
    ) -> Dict[str, Any]:
        """创建基金分析任务（立即返回，不执行分析）"""
        task_id = str(uuid.uuid4())
        ts_code = request.ts_code
        fund_name = request.fund_name or ts_code

        logger.info(f"📝 [基金分析] 创建任务: {task_id} - {ts_code}")

        # 在内存中创建任务状态
        params = request.parameters.model_dump() if request.parameters else {}
        params["ts_code"] = ts_code
        params["fund_name"] = fund_name

        await self.memory_manager.create_task(
            task_id=task_id,
            user_id=user_id,
            stock_code=ts_code,
            stock_name=fund_name,
            parameters=params,
        )

        # 写入 MongoDB
        db = get_mongo_db()
        await db.analysis_tasks.update_one(
            {"task_id": task_id},
            {
                "$set": {
                    "task_id": task_id,
                    "user_id": user_id,
                    "stock_code": ts_code,
                    "stock_name": fund_name,
                    "stock_symbol": ts_code,
                    "status": AnalysisStatus.PENDING.value,
                    "progress": 0,
                    "message": "基金分析任务已创建，等待执行...",
                    "current_step": "pending",
                    "parameters": params,
                    "task_type": "fund_analysis",
                    "created_at": datetime.utcnow(),
                    "started_at": None,
                    "completed_at": None,
                }
            },
            upsert=True,
        )

        return {
            "task_id": task_id,
            "status": "pending",
            "ts_code": ts_code,
            "fund_name": fund_name,
            "message": "基金分析任务已创建",
        }

    async def execute_fund_analysis_background(
        self,
        task_id: str,
        user_id: str,
        request: FundAnalysisRequest,
    ):
        """在后台执行基金分析任务"""
        ts_code = request.ts_code
        fund_name = request.fund_name or ts_code
        parameters = request.parameters

        logger.info(f"🚀 [基金分析] 开始执行任务: {task_id} - {ts_code}")
        start_time = datetime.now()

        try:
            # 更新任务状态为运行中
            await self._update_progress(task_id, 5, "正在准备基金数据...")
            await self._update_mongo_task(task_id, {
                "status": "running",
                "started_at": datetime.utcnow(),
            })

            # 1. 获取基金数据
            await self._update_progress(task_id, 10, "正在获取基金详情...")
            adapter = get_fund_data_adapter()
            fund_detail = await adapter.get_fund_detail(ts_code)

            if not fund_detail or not fund_detail.get("basic", {}).get("name"):
                raise ValueError(f"未找到基金 {ts_code} 的详细信息")

            await self._update_progress(task_id, 20, "基金数据获取完成")

            # 2. 获取模型配置
            research_depth = (parameters.research_depth if parameters else "标准") or "标准"
            selected_analysts = (parameters.selected_analysts if parameters else []) or ["净值分析师", "持仓分析师", "基金经理评估师"]
            quick_model = (parameters.quick_analysis_model if parameters else None) or "auto"
            deep_model = (parameters.deep_analysis_model if parameters else None) or "auto"

            capability_service = get_model_capability_service()
            if quick_model == "auto":
                quick_model, _ = capability_service.recommend_models_for_depth(research_depth)
            if deep_model == "auto":
                _, deep_model = capability_service.recommend_models_for_depth(research_depth)

            logger.info(f"🤖 [基金分析] 模型配置: quick={quick_model}, deep={deep_model}")

            # 3. 并行执行各分析师的独立分析
            analyst_reports = {}
            analyst_names = [a for a in selected_analysts if a in FUND_ANALYST_PROMPTS]
            if not analyst_names:
                analyst_names = ["净值分析师", "持仓分析师", "基金经理评估师"]

            total_analysts = len(analyst_names)
            for idx, analyst_name in enumerate(analyst_names):
                progress_base = 25 + (idx * 50 // total_analysts)
                await self._update_progress(task_id, progress_base, f"正在执行{analyst_name}的分析...")

                report = await self._call_analyst_llm(
                    analyst_name=analyst_name,
                    fund_detail=fund_detail,
                    quick_model=quick_model,
                )
                analyst_reports[analyst_name] = report
                logger.info(f"✅ [基金分析] {analyst_name} 完成 ({len(report)} 字)")

            # 4. 综合报告（调用深度模型）
            await self._update_progress(task_id, 80, "正在生成综合分析报告...")
            comprehensive_report = await self._generate_comprehensive_report(
                fund_detail=fund_detail,
                analyst_reports=analyst_reports,
                deep_model=deep_model,
            )

            await self._update_progress(task_id, 90, "正在整理分析结果...")

            # 5. 解析结构化结果
            result = self._parse_comprehensive_report(
                ts_code=ts_code,
                fund_detail=fund_detail,
                comprehensive_report=comprehensive_report,
                analyst_reports=analyst_reports,
            )
            result.execution_time = (datetime.now() - start_time).total_seconds()
            result.model_info = f"quick:{quick_model},deep:{deep_model}"

            # 6. 保存结果
            await self._save_result(task_id, user_id, result)

            # 7. 更新任务完成状态
            elapsed = (datetime.now() - start_time).total_seconds()
            result_dict = result.model_dump()
            # 兼容股票分析结果端点的字段命名
            result_dict["stock_symbol"] = result.ts_code
            result_dict["stock_code"] = result.ts_code
            result_dict["reports"] = {
                "comprehensive_report": result.comprehensive_report or "",
                "nav_trend": result.nav_trend or "",
                "holdings_analysis": result.holdings_analysis or "",
                "manager_assessment": result.manager_assessment or "",
                "risk_assessment": result.risk_assessment or "",
            }
            await self.memory_manager.update_task_status(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                progress=100,
                message="基金分析完成",
                current_step="completed",
                result_data=result_dict,
            )
            await self._update_mongo_task(task_id, {
                "status": AnalysisStatus.COMPLETED.value,
                "progress": 100,
                "completed_at": datetime.utcnow(),
                "execution_time": elapsed,
            })

            logger.info(f"✅ [基金分析] 任务完成: {task_id} - 耗时 {elapsed:.1f}s")

        except Exception as e:
            logger.error(f"❌ [基金分析] 任务失败: {task_id} - {e}", exc_info=True)
            await self.memory_manager.update_task_status(
                task_id=task_id,
                status=TaskStatus.FAILED,
                progress=0,
                message=f"分析失败: {str(e)}",
                current_step="failed",
            )
            await self._update_mongo_task(task_id, {
                "status": AnalysisStatus.FAILED.value,
                "error_message": str(e),
                "completed_at": datetime.utcnow(),
            })

    async def _update_progress(self, task_id: str, progress: int, message: str):
        """更新任务进度"""
        try:
            await self.memory_manager.update_task_status(
                task_id=task_id,
                status=TaskStatus.RUNNING,
                progress=progress,
                message=message,
                current_step=message,
            )
        except Exception as e:
            logger.warning(f"⚠️ [基金分析] 更新进度失败: {e}")

    async def _update_mongo_task(self, task_id: str, update_data: Dict[str, Any]):
        """更新 MongoDB 任务记录"""
        try:
            db = get_mongo_db()
            update_data["updated_at"] = datetime.utcnow()
            await db.analysis_tasks.update_one(
                {"task_id": task_id},
                {"$set": update_data}
            )
        except Exception as e:
            logger.warning(f"⚠️ [基金分析] 更新 MongoDB 失败: {e}")

    async def _call_analyst_llm(
        self,
        analyst_name: str,
        fund_detail: Dict[str, Any],
        quick_model: str,
    ) -> str:
        """调用单个分析师的 LLM"""
        analyst_config = FUND_ANALYST_PROMPTS.get(analyst_name)
        if not analyst_config:
            return f"未找到 {analyst_name} 的配置"

        # 构建提示词
        prompt = self._build_analyst_prompt(analyst_name, analyst_config, fund_detail)

        # 调用 LLM
        def _invoke():
            from tradingagents.llm_clients import create_llm_client
            from langchain_core.messages import SystemMessage, HumanMessage

            provider_info = get_provider_and_url_by_model_sync(quick_model)
            provider_key = normalize_provider_key(provider_info["provider"])

            llm_client = create_llm_client(
                provider=provider_key,
                model=quick_model,
                base_url=provider_info["backend_url"],
                api_key=provider_info["api_key"],
                temperature=0.3,
                max_tokens=4000,
            )
            llm = llm_client.get_llm()
            messages = [
                SystemMessage(content=analyst_config["role"]),
                HumanMessage(content=prompt),
            ]
            response = llm.invoke(messages)
            return response.content if hasattr(response, "content") else str(response)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._thread_pool, _invoke)

    def _build_analyst_prompt(self, analyst_name: str, config: Dict, fund_detail: Dict) -> str:
        """构建单个分析师的提示词"""
        basic = fund_detail.get("basic", {})
        latest_nav = fund_detail.get("latest_nav", {})
        nav_history = fund_detail.get("nav_history", [])[:10]
        managers = fund_detail.get("managers", [])
        latest_share = fund_detail.get("latest_share", {})

        nav_history_text = "\n".join([
            f"  {item.get('nav_date')}: 单位净值={item.get('nav')}, 日涨跌={item.get('daily_return')}"
            for item in nav_history
        ]) if nav_history else "暂无历史净值数据"

        manager_text = "\n".join([
            f"  - {m.get('name', '未知')}"
            f"{' | ' + m.get('company', '') if m.get('company') else ''}"
            f"{' | 任职' + m.get('tenure', '') if m.get('tenure') else ''}"
            for m in managers
        ]) if managers else "暂无基金经理数据"

        return f"""# 基金分析数据

## 基金基础信息
- 基金代码: {fund_detail.get('ts_code', '未知')}
- 基金名称: {basic.get('name', '未知')}
- 基金类型: {basic.get('fund_type', '未知')}
- 投资类型: {basic.get('invest_type', '未知')}
- 成立日期: {basic.get('found_date', '未知')}
- 管理人: {basic.get('management', '未知')}
- 托管人: {basic.get('custodian', '未知')}
- 业绩基准: {basic.get('benchmark', '未知')}

## 最新净值
- 净值日期: {latest_nav.get('nav_date', '未知')}
- 单位净值: {latest_nav.get('nav', '未知')}
- 累计净值: {latest_nav.get('acc_nav', '未知')}
- 日涨跌幅: {latest_nav.get('daily_return', '未知')}

## 近期净值明细
{nav_history_text}

## 基金经理
{manager_text}

## 规模信息
- 最新规模: {latest_share.get('fd_share', '未知')} (日期: {latest_share.get('trade_date', '未知')})

## 费率信息
- 管理费: {basic.get('m_fee', '未知')}%
- 托管费: {basic.get('c_fee', '未知')}%

---

{config['focus']}

请用中文输出，结构清晰，分析客观。字数控制在 800-1500 字。"""

    async def _generate_comprehensive_report(
        self,
        fund_detail: Dict[str, Any],
        analyst_reports: Dict[str, str],
        deep_model: str,
    ) -> str:
        """生成综合分析报告"""
        basic = fund_detail.get("basic", {})

        # 整合各分析师报告
        reports_section = "\n\n".join([
            f"### {name}的报告\n{report}"
            for name, report in analyst_reports.items()
        ])

        prompt = f"""# 基金综合分析任务

你是一位资深基金研究总监，需要综合各分析师的报告，生成一份专业的基金投资分析报告。

## 基金信息
- 基金代码: {fund_detail.get('ts_code')}
- 基金名称: {basic.get('name')}
- 基金类型: {basic.get('fund_type')}

## 各维度分析师报告

{reports_section}

---

## 综合报告要求

请基于以上各分析师的报告，生成一份结构化的综合投资分析报告，包含以下部分：

### 1. 投资摘要（200字以内）
一句话概括该基金的核心投资价值和主要风险。

### 2. 综合评分（1-10分）
给出综合评分并说明理由。

### 3. 投资建议（重点）
- 评级：强烈买入 / 买入 / 持有 / 卖出
- 适合的投资者类型
- 建议配置比例
- 关注要点

### 4. 核心风险提醒
列出投资该基金需要特别注意的风险。

### 5. 关键数据指标
- 最新净值、日涨跌幅
- 基金经理、管理公司
- 费率水平

请用中文输出，结构清晰，建议具体可操作。"""

        def _invoke():
            from tradingagents.llm_clients import create_llm_client
            from langchain_core.messages import SystemMessage, HumanMessage

            provider_info = get_provider_and_url_by_model_sync(deep_model)
            provider_key = normalize_provider_key(provider_info["provider"])

            llm_client = create_llm_client(
                provider=provider_key,
                model=deep_model,
                base_url=provider_info["backend_url"],
                api_key=provider_info["api_key"],
                temperature=0.3,
                max_tokens=8000,
            )
            llm = llm_client.get_llm()
            messages = [
                SystemMessage(content="你是一位资深基金研究总监，擅长综合多维度分析并给出权威投资建议。"),
                HumanMessage(content=prompt),
            ]
            response = llm.invoke(messages)
            return response.content if hasattr(response, "content") else str(response)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._thread_pool, _invoke)

    def _parse_comprehensive_report(
        self,
        ts_code: str,
        fund_detail: Dict[str, Any],
        comprehensive_report: str,
        analyst_reports: Dict[str, str],
    ) -> FundAnalysisResult:
        """解析综合分析报告为结构化结果"""
        basic = fund_detail.get("basic", {})

        # 提取投资建议（简单规则提取）
        recommendation = "请查看完整报告"
        for keyword in ["强烈买入", "买入", "持有", "卖出"]:
            if keyword in comprehensive_report:
                recommendation = f"建议{keyword}"
                break

        # 提取摘要（取前500字）
        summary = comprehensive_report[:500] if comprehensive_report else ""

        # 提取关键点
        key_points = []
        for line in comprehensive_report.split("\n"):
            line = line.strip()
            if line.startswith("-") or line.startswith("•") or line.startswith("*"):
                clean = line.lstrip("-•* ").strip()
                if clean and len(clean) > 10:
                    key_points.append(clean)
        if not key_points:
            key_points = ["基金分析已完成，请查看详细报告"]
        key_points = key_points[:8]

        return FundAnalysisResult(
            analysis_id=str(uuid.uuid4()),
            ts_code=ts_code,
            fund_name=basic.get("name"),
            fund_type=basic.get("fund_type"),
            summary=summary,
            recommendation=recommendation,
            comprehensive_report=comprehensive_report,
            nav_trend=analyst_reports.get("净值分析师", ""),
            holdings_analysis=analyst_reports.get("持仓分析师", ""),
            manager_assessment=analyst_reports.get("基金经理评估师", ""),
            risk_assessment=analyst_reports.get("风险评估师", ""),
            key_points=key_points,
        )

    async def _save_result(self, task_id: str, user_id: str, result: FundAnalysisResult):
        """保存分析结果到 MongoDB"""
        try:
            db = get_mongo_db()

            # 保存到 analysis_reports 集合
            report_doc = {
                "analysis_id": result.analysis_id or task_id,
                "task_id": task_id,
                "user_id": user_id,
                "stock_symbol": result.ts_code,
                "stock_code": result.ts_code,
                "analysis_date": datetime.utcnow(),
                "summary": result.summary or "",
                "recommendation": result.recommendation or "",
                "confidence_score": 0.0,
                "risk_level": "中等",
                "key_points": result.key_points or [],
                "execution_time": result.execution_time,
                "tokens_used": result.tokens_used,
                "analysts": [result.model_info] if result.model_info else [],
                "research_depth": "标准",
                "reports": {
                    "comprehensive_report": result.comprehensive_report or "",
                    "nav_trend": result.nav_trend or "",
                    "holdings_analysis": result.holdings_analysis or "",
                    "manager_assessment": result.manager_assessment or "",
                    "risk_assessment": result.risk_assessment or "",
                },
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "status": "completed",
                "task_type": "fund_analysis",
            }
            await db.analysis_reports.insert_one(report_doc)

            # 更新 analysis_tasks 的 result 字段
            await db.analysis_tasks.update_one(
                {"task_id": task_id},
                {
                    "$set": {
                        "result": result.model_dump(),
                        "analysis_id": result.analysis_id or task_id,
                    }
                }
            )

            logger.info(f"💾 [基金分析] 结果已保存: {task_id}")
        except Exception as e:
            logger.error(f"❌ [基金分析] 保存结果失败: {task_id} - {e}")


# 全局服务实例
_fund_analysis_task_service = None


def get_fund_analysis_task_service() -> FundAnalysisTaskService:
    """获取全局基金分析任务服务实例"""
    global _fund_analysis_task_service
    if _fund_analysis_task_service is None:
        _fund_analysis_task_service = FundAnalysisTaskService()
    return _fund_analysis_task_service
