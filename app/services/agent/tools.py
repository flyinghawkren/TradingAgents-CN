"""
智能投资 Agent - 工具定义

每个工具是一个可被 Agent 调用的能力单元，定义格式：
- name: 工具名称
- description: 工具描述（LLM 理解用途）
- parameters: 参数列表
- handler: 实际执行函数
"""
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
import logging

logger = logging.getLogger("app.services.agent.tools")


@dataclass
class ToolParameter:
    name: str
    type: str  # string, number, boolean
    description: str
    required: bool = False


@dataclass
class Tool:
    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)
    handler: Optional[Callable] = None


class ToolRegistry:
    """工具注册中心"""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool
        logger.info(f"🔧 注册工具: {tool.name} - {tool.description}")

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": [
                    {"name": p.name, "type": p.type, "description": p.description, "required": p.required}
                    for p in t.parameters
                ]
            }
            for t in self._tools.values()
        ]

    def execute(self, name: str, kwargs: Dict[str, Any], user_id: str) -> Any:
        tool = self.get(name)
        if not tool or not tool.handler:
            raise ValueError(f"未知工具: {name}")

        # 只传递工具定义中声明的参数，忽略 LLM 额外生成的参数
        allowed = {p.name for p in tool.parameters}
        filtered = {k: v for k, v in kwargs.items() if k in allowed}
        logger.debug(f"执行工具 {name}: 原始参数={kwargs}, 过滤后={filtered}")
        return tool.handler(user_id=user_id, **filtered)


# 全局注册中心
registry = ToolRegistry()
