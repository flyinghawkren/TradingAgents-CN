import os


def _get_default_llm_config():
    """根据 .env 环境变量动态获取默认LLM配置

    优先级：
    1. DeepSeek (如果 DEEPSEEK_ENABLED=true)
    2. 阿里百炼 (如果 DASHSCOPE_ENABLED=true)
    3. OpenAI (如果 OPENAI_ENABLED=true)
    4. 其他供应商
    5. 回退到 OpenAI（如果以上都未启用，保持向后兼容）
    """
    # 检查各供应商启用状态
    providers = [
        ("deepseek", "deepseek-chat", "deepseek-chat", "https://api.deepseek.com", "DEEPSEEK_ENABLED"),
        ("qwen", "qwen-turbo", "qwen-plus", "https://dashscope.aliyuncs.com/compatible-mode/v1", "DASHSCOPE_ENABLED"),
        ("openai", "gpt-4o-mini", "o4-mini", "https://api.openai.com/v1", "OPENAI_ENABLED"),
        ("google", "gemini-2.0-flash", "gemini-2.5-pro", "https://generativelanguage.googleapis.com/v1beta", "GOOGLE_ENABLED"),
        ("glm", "glm-4", "glm-4", "https://open.bigmodel.cn/api/paas/v4/", "ZHIPU_ENABLED"),
        ("qianfan", "ernie-bot", "ernie-bot-4", "https://qianfan.baidubce.com/v2", "QIANFAN_ENABLED"),
    ]

    for provider, quick_model, deep_model, base_url, env_key in providers:
        if os.getenv(env_key, "").lower() == "true":
            return {
                "llm_provider": provider,
                "quick_think_llm": quick_model,
                "deep_think_llm": deep_model,
                "backend_url": os.getenv(f"{provider.upper()}_BASE_URL", base_url),
            }

    # 如果没有启用的供应商，检查是否有 API Key 配置（向后兼容）
    if os.getenv("DEEPSEEK_API_KEY") and os.getenv("DEEPSEEK_API_KEY", "").strip() not in ("", "your_deepseek_api_key_here"):
        return {
            "llm_provider": "deepseek",
            "quick_think_llm": "deepseek-chat",
            "deep_think_llm": "deepseek-chat",
            "backend_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        }

    if os.getenv("DASHSCOPE_API_KEY") and os.getenv("DASHSCOPE_API_KEY", "").strip() not in ("", "your_dashscope_api_key_here"):
        return {
            "llm_provider": "qwen",
            "quick_think_llm": "qwen-turbo",
            "deep_think_llm": "qwen-plus",
            "backend_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        }

    # 最终回退到 OpenAI（保持向后兼容）
    return {
        "llm_provider": "openai",
        "quick_think_llm": "gpt-4o-mini",
        "deep_think_llm": "o4-mini",
        "backend_url": "https://api.openai.com/v1",
    }


_llm_defaults = _get_default_llm_config()

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    "data_dir": os.path.join(os.path.expanduser("~"), "Documents", "TradingAgents", "data"),
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    # LLM settings - 动态根据 .env 环境变量选择
    "llm_provider": _llm_defaults["llm_provider"],
    "deep_think_llm": _llm_defaults["deep_think_llm"],
    "quick_think_llm": _llm_defaults["quick_think_llm"],
    "backend_url": _llm_defaults["backend_url"],
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # Tool settings - 从环境变量读取，提供默认值
    "online_tools": os.getenv("ONLINE_TOOLS_ENABLED", "false").lower() == "true",
    "online_news": os.getenv("ONLINE_NEWS_ENABLED", "true").lower() == "true",
    "realtime_data": os.getenv("REALTIME_DATA_ENABLED", "false").lower() == "true",

    # Note: Database and cache configuration is now managed by .env file and config.database_manager
    # No database/cache settings in default config to avoid configuration conflicts
}
