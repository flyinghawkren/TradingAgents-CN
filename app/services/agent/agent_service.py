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

        # ----- 个股分析 -----
        registry.register(Tool(
            name="search_stock",
            description="通过股票名称或代码从本地数据库搜索股票（返回代码、名称等信息）",
            parameters=[
                ToolParameter(name="keyword", type="string", description="搜索关键词（股票名称或代码）", required=True),
            ],
            handler=self._handle_search_stock,
        ))

        registry.register(Tool(
            name="trigger_stock_analysis",
            description="触发单只股票的 AI 分析（异步任务，返回 task_id 和股票信息）。可只传名称自动查代码，或直接传代码。",
            parameters=[
                ToolParameter(name="stock_code", type="string", description="股票代码，如 000063。如果只有名称不传代码，会自动从数据库查找", required=False),
                ToolParameter(name="stock_name", type="string", description="股票名称，如 中兴通讯", required=False),
            ],
            handler=self._handle_trigger_stock_analysis,
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

    async def _handle_search_stock(self, user_id: str, keyword: str) -> List[Dict[str, Any]]:
        """从本地 stock_basics 搜索股票"""
        try:
            from app.services.basics_info_sync_service import get_basics_info_sync_service
            service = get_basics_info_sync_service()
            results = await service.get_stock_basics(keyword=keyword, limit=10)
            return [
                {"ts_code": r.get("ts_code", ""), "symbol": r.get("symbol", ""), "name": r.get("name", "")}
                for r in results if r.get("name")
            ]
        except Exception as e:
            logger.error(f"搜索股票失败: {e}")
            return []

    async def _handle_trigger_stock_analysis(self, user_id: str, stock_code: str = "", stock_name: str = "") -> Dict[str, Any]:
        """触发单股 AI 分析（支持只传名称自动查代码）"""
        try:
            # 如果只有名称没有代码，自动查询
            if not stock_code and stock_name:
                from app.services.basics_info_sync_service import get_basics_info_sync_service
                service = get_basics_info_sync_service()
                results = await service.get_stock_basics(keyword=stock_name, limit=5)
                for r in results:
                    name = (r.get("name") or "").strip()
                    if stock_name in name:
                        stock_code = r.get("symbol") or r.get("ts_code", "")
                        if "." in stock_code:
                            stock_code = stock_code.split(".")[0]
                        break
                if not stock_code and results:
                    r = results[0]
                    stock_code = r.get("symbol") or r.get("ts_code", "")
                    if "." in stock_code:
                        stock_code = stock_code.split(".")[0]

            if not stock_code:
                return {"error": "无法确定股票代码，请提供股票代码或更准确的名称", "status": "failed"}

            from app.services.analysis_service import get_analysis_service
            from app.models.analysis import SingleAnalysisRequest, AnalysisParameters

            params = AnalysisParameters(
                market_type="A股",
                research_depth="标准",
                selected_analysts=[0, 1, 2],
            )
            request = SingleAnalysisRequest(
                symbol=stock_code,
                stock_code=stock_code,
                parameters=params,
            )
            service = get_analysis_service()
            result = await service.submit_single_analysis(user_id=user_id, request=request)
            return {
                "task_id": result.get("task_id", ""),
                "stock_code": stock_code,
                "stock_name": stock_name or stock_code,
                "status": "分析任务已提交，正在后台执行",
                "message": f"个股分析任务已提交，任务ID: {result.get('task_id', '')}。可在任务中心查看进度。"
            }
        except Exception as e:
            logger.error(f"触发个股分析失败: {e}")
            return {"error": f"触发分析失败: {str(e)}", "status": "failed"}

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

    async def _get_available_models(self) -> list:
        """获取可用模型列表，优先 unified_config，失败后降级到 MongoDB"""
        import os
        from tradingagents.llm_clients.provider_keys import env_key_for_provider
        from app.core.unified_config import unified_config

        _placeholder_keys = {
            "", "your-api-key", "your_deepseek_api_key_here", "your_dashscope_api_key_here",
            "your_openai_api_key_here", "your_google_api_key_here", "your_qianfan_api_key_here",
            "your_anthropic_api_key_here", "your_openrouter_api_key_here", "your_aihubmix_api_key_here",
            "your_zhipu_api_key_here", "your_siliconflow_api_key_here", "your_oneapi_api_key_here",
            "your-custom-openai-api-key",
        }

        def _has_valid_key(cfg) -> bool:
            if not getattr(cfg, 'enabled', True):
                return False
            env_var = env_key_for_provider(cfg.provider)
            if not env_var:
                return False
            key_val = os.getenv(env_var, "")
            return key_val.strip() not in _placeholder_keys

        # 尝试 unified_config（读取 models.json）
        try:
            configs = unified_config.get_llm_configs()
            available = [c for c in configs if _has_valid_key(cfg=c)]
            if available:
                return available
        except Exception as e:
            logger.warning(f"unified_config 获取模型失败: {e}")

        # 降级：直接从 MongoDB system_configs 读取
        try:
            from app.core.database import get_mongo_db
            from tradingagents.llm_clients.provider_keys import env_key_for_provider
            from app.core.unified_config import LLMConfig

            db = get_mongo_db()
            doc = await db.system_configs.find_one({}, sort=[('_id', -1)])
            if doc and "llm_configs" in doc:
                configs = []
                for m in doc["llm_configs"]:
                    provider = m.get("provider", "")
                    model_name = m.get("model_name", "")
                    enabled = m.get("enabled", False)
                    api_base = m.get("api_base", "")
                    max_tokens = m.get("max_tokens", 4000)
                    temperature = m.get("temperature", 0.7)

                    cfg = LLMConfig(
                        provider=provider,
                        model_name=model_name,
                        api_key="",
                        api_base=api_base,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        enabled=enabled,
                    )
                    configs.append(cfg)

                available = [c for c in configs if _has_valid_key(cfg=c)]
                if available:
                    logger.info(f"从 MongoDB 获取 {len(available)} 个可用模型")
                    return available
        except Exception as e:
            logger.warning(f"MongoDB 读取模型配置失败: {e}")

        # 全部失败，返回带所有 enabled 模型信息的错误消息
        enabled_list = []
        try:
            for c in configs if 'configs' in dir() else []:
                if c.enabled:
                    enabled_list.append(f"{c.model_name}({env_key_for_provider(c.provider)})")
        except Exception:
            pass

        raise RuntimeError(
            "暂无可用 AI 模型。启用的模型中均未发现有效的 API Key。\n"
            + (f"已启用: {', '.join(enabled_list)}" if enabled_list else "请前往设置配置 AI 模型。")
            + "\n\n请确保对应环境变量（如 DEEPSEEK_API_KEY）已在 .env 或容器环境中正确配置。"
        )

    async def _call_llm(self, prompt: str, system_prompt: str = "") -> str:
        """调用大模型——自动选择第一个启用且配置了 API Key 的模型"""
        import os
        from tradingagents.llm_clients import create_llm_client
        from langchain_core.messages import SystemMessage, HumanMessage
        from tradingagents.llm_clients.provider_keys import normalize_provider_key, env_key_for_provider

        try:
            available = await self._get_available_models()
        except RuntimeError as e:
            return str(e)
        except Exception as e:
            logger.error(f"获取可用模型失败: {e}")
            return f"获取可用模型失败: {e}"

        last_error = ""
        for cfg in available:
            try:
                env_var = env_key_for_provider(cfg.provider)
                api_key = os.getenv(env_var, "")

                provider_key = normalize_provider_key(cfg.provider)
                llm_client = create_llm_client(
                    provider=provider_key,
                    model=cfg.model_name,
                    base_url=cfg.api_base,
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

            except Exception as e:
                last_error = str(e)
                logger.warning(f"模型 {cfg.model_name} 调用失败: {e}，尝试下一个...")
                continue

        return f"所有可用模型调用均失败。最后错误: {last_error}"

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
