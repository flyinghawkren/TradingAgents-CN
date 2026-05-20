"""
智能投资 Agent 服务

架构：
1. 接收用户消息 → 意图识别（路由到工具或 LLM）
2. 工具执行：调用注册的后端能力获取数据
3. LLM 综合：调用大模型对数据进行综合分析
4. 返回结构化响应
"""
import json
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from app.services.agent.tools import Tool, ToolParameter, registry
from app.services.portfolio_service import portfolio_service
from app.services.agent.tools import registry as tool_registry

logger = logging.getLogger("app.services.agent")


@dataclass
class AgentContext:
    user_id: str
    conversation: List[Dict[str, str]] = field(default_factory=list)


class AgentService:
    """智能投资 Agent 服务"""

    def __init__(self):
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        """注册内置工具"""

        # ----- 投资组合工具 -----
        registry.register(Tool(
            name="get_portfolio_overview",
            description="获取用户投资组合概览（股票+基金+现金总数及总市值）",
            handler=self._handle_portfolio_overview,
        ))

        registry.register(Tool(
            name="get_stock_holdings",
            description="获取持仓股票列表及详情",
            parameters=[
                ToolParameter(name="keyword", type="string", description="搜索关键词（代码或名称）", required=False),
            ],
            handler=self._handle_stock_holdings,
        ))

        registry.register(Tool(
            name="get_fund_holdings",
            description="获取持仓基金列表及详情",
            parameters=[
                ToolParameter(name="keyword", type="string", description="搜索关键词（代码或名称）", required=False),
            ],
            handler=self._handle_fund_holdings,
        ))

        registry.register(Tool(
            name="get_cash_accounts",
            description="获取现金账户列表",
            handler=self._handle_cash_accounts,
        ))

        # ----- 投资偏好 -----
        registry.register(Tool(
            name="get_investment_preference",
            description="获取用户的投资风险偏好（保守型/谨慎型/稳健型/进取型/激进型）",
            handler=self._handle_investment_preference,
        ))

        # ----- 分析报告 -----
        registry.register(Tool(
            name="get_analysis_reports",
            description="获取历史分析报告列表",
            parameters=[
                ToolParameter(name="limit", type="number", description="获取数量", required=False),
            ],
            handler=self._handle_analysis_reports,
        ))

        registry.register(Tool(
            name="get_report_detail",
            description="获取指定分析报告的详细内容",
            parameters=[
                ToolParameter(name="report_id", type="string", description="报告 ID", required=True),
            ],
            handler=self._handle_report_detail,
        ))

        # ----- 投资建议 -----
        registry.register(Tool(
            name="get_investment_advice",
            description="基于投资偏好和持仓情况生成个性化投资建议",
            handler=self._handle_investment_advice,
        ))

    # ==================== Tool Handlers ====================

    async def _handle_portfolio_overview(self, user_id: str) -> Dict[str, Any]:
        try:
            stocks = await portfolio_service.get_user_holdings(user_id)
            funds = await portfolio_service.get_user_fund_holdings(user_id)
            cash = await portfolio_service.get_user_cash(user_id)

            stock_value = sum(s.get("quantity", 0) * (s.get("avg_price", 0) or 0) for s in stocks)
            fund_value = sum(f.get("quantity", 0) * (f.get("avg_nav", 0) or 0) for f in funds)
            cash_cny = 0
            for c in cash:
                rate = {"CNY": 1, "USD": 7.2, "HKD": 0.92}.get(c.get("currency", "CNY"), 1)
                cash_cny += c.get("amount", 0) * rate

            return {
                "stock_count": len(stocks),
                "fund_count": len(funds),
                "cash_count": len(cash),
                "stock_value_cny": round(stock_value, 2),
                "fund_value_cny": round(fund_value, 2),
                "cash_value_cny": round(cash_cny, 2),
                "total_value_cny": round(stock_value + fund_value + cash_cny, 2),
            }
        except Exception as e:
            logger.error(f"获取投资组合概览失败: {e}")
            return {"error": str(e)}

    async def _handle_stock_holdings(self, user_id: str, keyword: str = "") -> List[Dict[str, Any]]:
        try:
            stocks = await portfolio_service.get_user_holdings(user_id)
            if keyword:
                kw = keyword.lower()
                stocks = [s for s in stocks if kw in s.get("stock_code", "").lower() or kw in s.get("stock_name", "").lower()]
            return stocks
        except Exception as e:
            logger.error(f"获取持仓股票失败: {e}")
            return []

    async def _handle_fund_holdings(self, user_id: str, keyword: str = "") -> List[Dict[str, Any]]:
        try:
            funds = await portfolio_service.get_user_fund_holdings(user_id)
            if keyword:
                kw = keyword.lower()
                funds = [f for f in funds if kw in f.get("fund_code", "").lower() or kw in f.get("fund_name", "").lower()]
            return funds
        except Exception as e:
            logger.error(f"获取持仓基金失败: {e}")
            return []

    async def _handle_cash_accounts(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            return await portfolio_service.get_user_cash(user_id)
        except Exception as e:
            logger.error(f"获取现金账户失败: {e}")
            return []

    async def _handle_investment_preference(self, user_id: str) -> Dict[str, Any]:
        try:
            from app.core.database import get_mongo_db
            db = get_mongo_db()
            doc = await db.user_settings.find_one({"user_id": user_id})
            pref = doc.get("investment_preference", "稳健型") if doc else "稳健型"
            tips = {
                "保守型": "低风险偏好，优先保障本金安全",
                "谨慎型": "较低风险偏好，可接受小幅波动",
                "稳健型": "中等风险偏好，追求稳健增值",
                "进取型": "较高风险偏好，可接受较大波动",
                "激进型": "高风险偏好，追求高收益回报",
            }
            return {"preference": pref, "description": tips.get(pref, "")}
        except Exception as e:
            logger.error(f"获取投资偏好失败: {e}")
            return {"preference": "稳健型", "description": "中等风险偏好，追求稳健增值"}

    async def _handle_analysis_reports(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            from app.services.queue_service import get_queue_service
            svc = await get_queue_service()
            tasks = await svc.get_user_tasks(user_id=user_id)
            completed = [t for t in tasks if t.get("status") == "completed"]
            completed.sort(key=lambda t: t.get("updated_at", "") or "", reverse=True)
            return [
                {
                    "task_id": t.get("task_id"),
                    "task_name": t.get("task_name", ""),
                    "task_type": t.get("task_type", ""),
                    "updated_at": t.get("updated_at"),
                }
                for t in completed[:limit]
            ]
        except Exception as e:
            logger.error(f"获取分析报告失败: {e}")
            return []

    async def _handle_report_detail(self, user_id: str, report_id: str) -> Dict[str, Any]:
        try:
            from app.services.queue_service import get_queue_service
            svc = await get_queue_service()
            task = await svc.get_task(report_id)
            if task and task.get("user") == user_id:
                return {
                    "task_id": task.get("task_id"),
                    "task_name": task.get("task_name"),
                    "task_type": task.get("task_type"),
                    "result": task.get("result"),
                    "created_at": task.get("created_at"),
                    "updated_at": task.get("updated_at"),
                }
            return {"error": "报告不存在或无权限访问"}
        except Exception as e:
            logger.error(f"获取报告详情失败: {e}")
            return {"error": str(e)}

    async def _handle_investment_advice(self, user_id: str) -> str:
        """生成投资建议（调用 LLM）"""
        try:
            overview = await self._handle_portfolio_overview(user_id)
            pref_data = await self._handle_investment_preference(user_id)
            stocks = await self._handle_stock_holdings(user_id)
            funds = await self._handle_fund_holdings(user_id)

            context = json.dumps({
                "overview": overview,
                "preference": pref_data,
                "stocks_count": len(stocks),
                "funds_count": len(funds),
            }, ensure_ascii=False, indent=2)

            prompt = (
                f"你是一位专业的投资顾问。请根据以下投资者信息，提供个性化的投资建议。\n\n"
                f"=== 投资者信息 ===\n{context}\n\n"
                f"请从以下方面进行分析：\n"
                f"1. 当前资产配置是否合理\n"
                f"2. 是否与投资偏好匹配\n"
                f"3. 优化建议\n\n"
                f"请用中文回答，简洁明了。"
            )

            return await self._call_llm(prompt)

        except Exception as e:
            logger.error(f"生成投资建议失败: {e}")
            return "抱歉，暂时无法生成投资建议，请稍后再试。"

    # ==================== LLM 调用 ====================

    async def _call_llm(self, prompt: str, system_prompt: str = "") -> str:
        """调用大模型"""
        try:
            from tradingagents.llm_clients import create_llm_client
            from langchain_core.messages import SystemMessage, HumanMessage
            from app.services.model_capability_service import get_model_capability_service
            from app.services.simple_analysis_service import get_provider_and_url_by_model_sync

            capability_service = get_model_capability_service()
            _, deep_model = capability_service.recommend_models_for_depth("标准")
            provider_info = get_provider_and_url_by_model_sync(deep_model)
            provider = provider_info["provider"]
            backend_url = provider_info["backend_url"]
            api_key = provider_info["api_key"]

            from app.services.analysis_service import normalize_provider_key
            provider_key = normalize_provider_key(provider)
            llm_client = create_llm_client(
                provider=provider_key,
                model=deep_model,
                base_url=backend_url,
                api_key=api_key,
                temperature=0.7,
                max_tokens=4000,
            )

            llm = llm_client.get_llm()
            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=prompt))

            import asyncio
            response = await asyncio.to_thread(llm.invoke, messages)
            return response.content if hasattr(response, "content") else str(response)

        except ImportError as e:
            return f"无法加载 LLM 客户端，请确认已安装依赖。错误: {e}"
        except Exception as e:
            return f"调用大模型时出错: {e}"

    # ==================== 主入口 ====================

    async def chat(self, message: str, user_id: str) -> Dict[str, Any]:
        """处理用户消息并返回响应"""
        message_lower = message.strip().lower()

        # 尝试调用 LLM 进行意图识别和回复
        try:
            tool_descriptions = "\n".join(
                f"- {t['name']}: {t['description']}"
                for t in tool_registry.list_tools()
            )

            system = (
                "你是一个智能投资助手。你可以使用以下工具来获取投资者信息。"
                "请判断用户的问题是否需要调用工具来获取数据。\n\n"
                "可用工具：\n" + tool_descriptions + "\n\n"
                "如果用户问题需要数据支持，请回复 JSON 格式：{\"tool\": \"工具名\", \"params\": {...}}\n"
                "如果可以直接回答，请用自然语言回复。"
            )

            llm_response = await self._call_llm(message, system_prompt=system)

            # 检查是否是工具调用请求
            if llm_response.strip().startswith("{"):
                try:
                    cmd = json.loads(llm_response)
                    tool_name = cmd.get("tool")
                    params = cmd.get("params", {})

                    if tool_name:
                        # 执行工具
                        tool_data = await tool_registry.execute(tool_name, params, user_id)

                        # 用 LLM 综合工具结果生成回答
                        summary_prompt = (
                            f"用户问题: {message}\n\n"
                            f"查询结果: {json.dumps(tool_data, ensure_ascii=False, indent=2)}\n\n"
                            f"请基于以上查询结果，用自然语言回答用户的问题。"
                        )
                        reply = await self._call_llm(summary_prompt)
                        return {"reply": reply}
                except json.JSONDecodeError:
                    pass

            # LLM 直接回答
            return {"reply": llm_response}

        except Exception as e:
            logger.error(f"Agent 处理失败: {e}", exc_info=True)
            return {"reply": f"抱歉，处理您的请求时出错: {str(e)}"}


# 全局单例
_agent_service: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service
