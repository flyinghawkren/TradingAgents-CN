"""
统一配置管理系统
整合 config/、tradingagents/config/ 和 webapi 的配置管理
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import asyncio
from dataclasses import dataclass, asdict

from app.models.config import (
    LLMConfig, DataSourceConfig, DatabaseConfig, SystemConfig,
    ModelProvider, DataSourceType, DatabaseType
)


@dataclass
class ConfigPaths:
    """配置文件路径"""
    root_config_dir: Path = Path("config")
    tradingagents_config_dir: Path = Path("tradingagents/config")
    webapi_config_dir: Path = Path("data/config")
    
    # 具体配置文件
    models_json: Path = root_config_dir / "models.json"
    settings_json: Path = root_config_dir / "settings.json"
    pricing_json: Path = root_config_dir / "pricing.json"
    verified_models_json: Path = root_config_dir / "verified_models.json"


class UnifiedConfigManager:
    """统一配置管理器"""
    
    def __init__(self):
        self.paths = ConfigPaths()
        self._cache = {}
        self._last_modified = {}
        
    def _get_file_mtime(self, file_path: Path) -> float:
        """获取文件修改时间"""
        try:
            return file_path.stat().st_mtime
        except FileNotFoundError:
            return 0.0
    
    def _is_cache_valid(self, cache_key: str, file_path: Path) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self._cache:
            return False
        
        current_mtime = self._get_file_mtime(file_path)
        cached_mtime = self._last_modified.get(cache_key, 0)
        
        return current_mtime <= cached_mtime
    
    def _load_json_file(self, file_path: Path, cache_key: str = None) -> Dict[str, Any]:
        """加载JSON文件，支持缓存"""
        if cache_key and self._is_cache_valid(cache_key, file_path):
            return self._cache[cache_key]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if cache_key:
                self._cache[cache_key] = data
                self._last_modified[cache_key] = self._get_file_mtime(file_path)
            
            return data
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as e:
            print(f"配置文件格式错误 {file_path}: {e}")
            return {}
    
    def _save_json_file(self, file_path: Path, data: Dict[str, Any], cache_key: str = None):
        """保存JSON文件"""
        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        if cache_key:
            self._cache[cache_key] = data
            self._last_modified[cache_key] = self._get_file_mtime(file_path)
    
    # ==================== 模型配置管理 ====================
    
    def get_legacy_models(self) -> List[Dict[str, Any]]:
        """获取传统格式的模型配置"""
        return self._load_json_file(self.paths.models_json, "models")
    
    def _infer_provider_from_model_name(self, model_name: str) -> str:
        """根据模型名称推断供应商"""
        model_name_lower = model_name.lower()
        provider_map = {
            "deepseek": "deepseek",
            "qwen": "qwen",
            "gpt": "openai",
            "o1": "openai",
            "o3": "openai",
            "o4": "openai",
            "gemini": "google",
            "glm": "glm",
            "claude": "anthropic",
        }
        for key, provider in provider_map.items():
            if key in model_name_lower:
                return provider
        return ""

    def _get_env_enabled_models(self) -> List[LLMConfig]:
        """根据 .env 环境变量动态生成启用的模型配置"""
        env_models = []

        # DeepSeek
        if os.getenv("DEEPSEEK_ENABLED", "").lower() == "true":
            env_models.append(LLMConfig(
                provider="deepseek",
                model_name="deepseek-chat",
                api_key="",
                api_base=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                max_tokens=8000,
                temperature=0.7,
                enabled=True,
                description="DeepSeek 对话模型"
            ))

        # 阿里百炼 (DashScope)
        if os.getenv("DASHSCOPE_ENABLED", "").lower() == "true":
            env_models.append(LLMConfig(
                provider="qwen",
                model_name="qwen-turbo",
                api_key="",
                api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
                max_tokens=4000,
                temperature=0.7,
                enabled=True,
                description="阿里百炼 qwen-turbo"
            ))

        # OpenAI
        if os.getenv("OPENAI_ENABLED", "").lower() == "true":
            env_models.append(LLMConfig(
                provider="openai",
                model_name="gpt-4o-mini",
                api_key="",
                api_base="https://api.openai.com/v1",
                max_tokens=4000,
                temperature=0.7,
                enabled=True,
                description="OpenAI GPT-4o-mini"
            ))

        # Google Gemini
        if os.getenv("GOOGLE_ENABLED", "").lower() == "true":
            env_models.append(LLMConfig(
                provider="google",
                model_name="gemini-2.0-flash",
                api_key="",
                api_base="https://generativelanguage.googleapis.com/v1beta",
                max_tokens=4000,
                temperature=0.7,
                enabled=True,
                description="Google Gemini 2.0 Flash"
            ))

        # 智谱AI
        if os.getenv("ZHIPU_ENABLED", "").lower() == "true" or os.getenv("GLM_ENABLED", "").lower() == "true":
            env_models.append(LLMConfig(
                provider="glm",
                model_name="glm-4",
                api_key="",
                api_base="https://open.bigmodel.cn/api/paas/v4/",
                max_tokens=4000,
                temperature=0.7,
                enabled=True,
                description="智谱AI GLM-4"
            ))

        # 百度千帆
        if os.getenv("QIANFAN_ENABLED", "").lower() == "true":
            env_models.append(LLMConfig(
                provider="qianfan",
                model_name="ernie-bot",
                api_key="",
                api_base="https://qianfan.baidubce.com/v2",
                max_tokens=4000,
                temperature=0.7,
                enabled=True,
                description="百度千帆 ERNIE Bot"
            ))

        return env_models

    def get_llm_configs(self) -> List[LLMConfig]:
        """获取标准化的LLM配置

        优先级：
        1. 读取 config/models.json 中的配置
        2. 如果 models.json 为空/不存在，根据 .env 环境变量动态生成
        """
        legacy_models = self.get_legacy_models()
        llm_configs = []

        for model in legacy_models:
            try:
                # 优先从 model_name 推断 provider，避免默认硬编码为 openai
                provider = model.get("provider", "")
                if not provider:
                    provider = self._infer_provider_from_model_name(
                        model.get("model_name", "")
                    )
                if not provider:
                    print(f"⚠️ [unified_config] 无法推断模型 {model.get('model_name')} 的供应商，跳过")
                    continue

                # 方案A：敏感密钥不从文件加载，统一走环境变量/厂家目录
                llm_config = LLMConfig(
                    provider=provider,
                    model_name=model.get("model_name", ""),
                    api_key="",
                    api_base=model.get("base_url"),
                    max_tokens=model.get("max_tokens", 4000),
                    temperature=model.get("temperature", 0.7),
                    enabled=model.get("enabled", True),
                    description=f"{provider} {model.get('model_name', '')}"
                )
                llm_configs.append(llm_config)
            except Exception as e:
                print(f"转换模型配置失败: {model}, 错误: {e}")
                continue

        # 🔧 如果 models.json 为空/不存在，根据 .env 动态生成模型配置
        if not llm_configs:
            print("⚠️ [unified_config] models.json 为空或不存在，尝试从 .env 环境变量生成模型配置")
            llm_configs = self._get_env_enabled_models()
            if llm_configs:
                print(f"✅ [unified_config] 从 .env 生成 {len(llm_configs)} 个模型配置")
            else:
                print("⚠️ [unified_config] .env 中未启用任何模型，使用系统默认配置")

        # 🔍 打印所有启用的模型及 API Key 状态
        print(f"\n{'='*60}")
        print(f"📋 [unified_config] 当前启用的模型列表 (共 {len(llm_configs)} 个)")
        for idx, cfg in enumerate(llm_configs, 1):
            enabled_flag = "✅ 启用" if getattr(cfg, 'enabled', True) else "❌ 禁用"
            # 从环境变量查找对应 API Key
            from tradingagents.llm_clients.provider_keys import env_key_for_provider
            env_key = env_key_for_provider(cfg.provider)
            api_key_val = os.getenv(env_key, "") if env_key else ""
            has_key = bool(api_key_val and api_key_val.strip() and api_key_val.strip() not in (
                "", "your-api-key", "your_deepseek_api_key_here", "your_dashscope_api_key_here",
                "your_openai_api_key_here", "your_google_api_key_here", "your_qianfan_api_key_here",
                "your_anthropic_api_key_here", "your_openrouter_api_key_here", "your_aihubmix_api_key_here",
                "your_zhipu_api_key_here", "your_siliconflow_api_key_here", "your_oneapi_api_key_here",
                "your-custom-openai-api-key"
            ))
            key_status = f"🟢 Key已配置 ({env_key})" if has_key else f"🔴 Key未配置 ({env_key})"
            print(f"   {idx}. {cfg.model_name:20s} | provider={cfg.provider:10s} | {enabled_flag} | {key_status}")
            if cfg.api_base:
                print(f"      api_base={cfg.api_base}")
        print(f"{'='*60}\n")

        return llm_configs
    
    def save_llm_config(self, llm_config: LLMConfig) -> bool:
        """保存LLM配置到传统格式"""
        try:
            legacy_models = self.get_legacy_models()

            # 直接使用 provider 字符串，不再需要映射
            # 方案A：保存到文件时不写入密钥
            legacy_model = {
                "provider": llm_config.provider,
                "model_name": llm_config.model_name,
                "api_key": "",
                "base_url": llm_config.api_base,
                "max_tokens": llm_config.max_tokens,
                "temperature": llm_config.temperature,
                "enabled": llm_config.enabled
            }
            
            # 查找并更新现有配置，或添加新配置
            updated = False
            for i, model in enumerate(legacy_models):
                if (model.get("provider") == legacy_model["provider"] and 
                    model.get("model_name") == legacy_model["model_name"]):
                    legacy_models[i] = legacy_model
                    updated = True
                    break
            
            if not updated:
                legacy_models.append(legacy_model)
            
            self._save_json_file(self.paths.models_json, legacy_models, "models")
            return True
            
        except Exception as e:
            print(f"保存LLM配置失败: {e}")
            return False
    
    # ==================== 系统设置管理 ====================
    
    def get_system_settings(self) -> Dict[str, Any]:
        """获取系统设置"""
        return self._load_json_file(self.paths.settings_json, "settings")
    
    def save_system_settings(self, settings: Dict[str, Any]) -> bool:
        """保存系统设置（保留现有字段，添加新字段映射）"""
        try:
            print(f"📝 [unified_config] save_system_settings 被调用")
            print(f"📝 [unified_config] 接收到的 settings 包含 {len(settings)} 项")

            # 检查关键字段
            if "quick_analysis_model" in settings:
                print(f"  ✓ [unified_config] 包含 quick_analysis_model: {settings['quick_analysis_model']}")
            else:
                print(f"  ⚠️  [unified_config] 不包含 quick_analysis_model")

            if "deep_analysis_model" in settings:
                print(f"  ✓ [unified_config] 包含 deep_analysis_model: {settings['deep_analysis_model']}")
            else:
                print(f"  ⚠️  [unified_config] 不包含 deep_analysis_model")

            # 读取现有配置
            print(f"📖 [unified_config] 读取现有配置文件: {self.paths.settings_json}")
            current_settings = self.get_system_settings()
            print(f"📖 [unified_config] 现有配置包含 {len(current_settings)} 项")

            # 合并配置（新配置覆盖旧配置）
            merged_settings = current_settings.copy()
            merged_settings.update(settings)
            print(f"🔀 [unified_config] 合并后配置包含 {len(merged_settings)} 项")

            # 添加字段名映射（新字段名 -> 旧字段名）
            if "quick_analysis_model" in settings:
                merged_settings["quick_think_llm"] = settings["quick_analysis_model"]
                print(f"  ✓ [unified_config] 映射 quick_analysis_model -> quick_think_llm: {settings['quick_analysis_model']}")

            if "deep_analysis_model" in settings:
                merged_settings["deep_think_llm"] = settings["deep_analysis_model"]
                print(f"  ✓ [unified_config] 映射 deep_analysis_model -> deep_think_llm: {settings['deep_analysis_model']}")

            # 打印最终要保存的配置
            print(f"💾 [unified_config] 即将保存到文件:")
            if "quick_think_llm" in merged_settings:
                print(f"  ✓ quick_think_llm: {merged_settings['quick_think_llm']}")
            if "deep_think_llm" in merged_settings:
                print(f"  ✓ deep_think_llm: {merged_settings['deep_think_llm']}")
            if "quick_analysis_model" in merged_settings:
                print(f"  ✓ quick_analysis_model: {merged_settings['quick_analysis_model']}")
            if "deep_analysis_model" in merged_settings:
                print(f"  ✓ deep_analysis_model: {merged_settings['deep_analysis_model']}")

            # 保存合并后的配置
            print(f"💾 [unified_config] 保存到文件: {self.paths.settings_json}")
            self._save_json_file(self.paths.settings_json, merged_settings, "settings")
            print(f"✅ [unified_config] 配置保存成功")

            return True
        except Exception as e:
            print(f"❌ [unified_config] 保存系统设置失败: {e}")
            import traceback
            print(traceback.format_exc())
            return False
    
    def get_default_model(self) -> str:
        """获取默认模型（向后兼容）"""
        settings = self.get_system_settings()
        # 优先返回快速分析模型，保持向后兼容
        return settings.get("quick_analysis_model", settings.get("default_model", "qwen-turbo"))

    def set_default_model(self, model_name: str) -> bool:
        """设置默认模型（向后兼容）"""
        settings = self.get_system_settings()
        settings["quick_analysis_model"] = model_name
        return self.save_system_settings(settings)

    def _get_first_enabled_model(self) -> str:
        """获取第一个启用的模型名称（从.env或配置文件）"""
        env_configs = self.get_llm_configs()
        enabled = [m for m in env_configs if getattr(m, 'enabled', True)]
        if enabled:
            return enabled[0].model_name
        return ""

    def get_quick_analysis_model(self) -> str:
        """获取快速分析模型——优先从配置读取，空时自动选择第一个可用模型"""
        settings = self.get_system_settings()
        model = settings.get("quick_analysis_model") or settings.get("quick_think_llm", "")
        if model:
            return model
        # 自动选择第一个可用模型
        first = self._get_first_enabled_model()
        if first:
            print(f"⚠️ [unified_config] quick_analysis_model 未配置，自动选择第一个可用模型: {first}")
        return first

    def get_deep_analysis_model(self) -> str:
        """获取深度分析模型——优先从配置读取，空时自动选择第一个可用模型"""
        settings = self.get_system_settings()
        model = settings.get("deep_analysis_model") or settings.get("deep_think_llm", "")
        if model:
            return model
        # 自动选择第一个可用模型
        first = self._get_first_enabled_model()
        if first:
            print(f"⚠️ [unified_config] deep_analysis_model 未配置，自动选择第一个可用模型: {first}")
        return first

    def set_analysis_models(self, quick_model: str, deep_model: str) -> bool:
        """设置分析模型"""
        settings = self.get_system_settings()
        settings["quick_analysis_model"] = quick_model
        settings["deep_analysis_model"] = deep_model
        return self.save_system_settings(settings)
    
    # ==================== 数据源配置管理 ====================
    
    def get_data_source_configs(self) -> List[DataSourceConfig]:
        """获取数据源配置 - 优先从数据库读取，回退到硬编码（同步版本）"""
        try:
            # 🔥 优先从数据库读取配置（使用同步连接）
            from app.core.database import get_mongo_db_sync
            db = get_mongo_db_sync()
            config_collection = db.system_configs

            # 获取最新的激活配置
            config_data = config_collection.find_one(
                {"is_active": True},
                sort=[("version", -1)]
            )

            if config_data and config_data.get('data_source_configs'):
                # 从数据库读取到配置
                data_source_configs = config_data.get('data_source_configs', [])
                print(f"✅ [unified_config] 从数据库读取到 {len(data_source_configs)} 个数据源配置")

                # 转换为 DataSourceConfig 对象
                result = []
                for ds_config in data_source_configs:
                    try:
                        result.append(DataSourceConfig(**ds_config))
                    except Exception as e:
                        print(f"⚠️ [unified_config] 解析数据源配置失败: {e}, 配置: {ds_config}")
                        continue

                # 按优先级排序（数字越大优先级越高）
                result.sort(key=lambda x: x.priority, reverse=True)
                return result
            else:
                print("⚠️ [unified_config] 数据库中没有数据源配置，使用硬编码配置")
        except Exception as e:
            print(f"⚠️ [unified_config] 从数据库读取数据源配置失败: {e}，使用硬编码配置")

        # 🔥 回退到硬编码配置（兼容性）
        settings = self.get_system_settings()
        data_sources = []

        # AKShare (默认启用)
        akshare_config = DataSourceConfig(
            name="AKShare",
            type=DataSourceType.AKSHARE,
            endpoint="https://akshare.akfamily.xyz",
            enabled=True,
            priority=1,
            description="AKShare开源金融数据接口"
        )
        data_sources.append(akshare_config)

        # Tushare (如果有配置)
        if settings.get("tushare_token"):
            tushare_config = DataSourceConfig(
                name="Tushare",
                type=DataSourceType.TUSHARE,
                api_key=settings.get("tushare_token"),
                endpoint="http://api.tushare.pro",
                enabled=True,
                priority=2,
                description="Tushare专业金融数据接口"
            )
            data_sources.append(tushare_config)

        # 按优先级排序
        data_sources.sort(key=lambda x: x.priority, reverse=True)
        return data_sources

    async def get_data_source_configs_async(self) -> List[DataSourceConfig]:
        """获取数据源配置 - 优先从数据库读取，回退到硬编码（异步版本）"""
        try:
            # 🔥 优先从数据库读取配置（使用异步连接）
            from app.core.database import get_mongo_db
            db = get_mongo_db()
            config_collection = db.system_configs

            # 获取最新的激活配置
            config_data = await config_collection.find_one(
                {"is_active": True},
                sort=[("version", -1)]
            )

            if config_data and config_data.get('data_source_configs'):
                # 从数据库读取到配置
                data_source_configs = config_data.get('data_source_configs', [])
                print(f"✅ [unified_config] 从数据库读取到 {len(data_source_configs)} 个数据源配置")

                # 转换为 DataSourceConfig 对象
                result = []
                for ds_config in data_source_configs:
                    try:
                        result.append(DataSourceConfig(**ds_config))
                    except Exception as e:
                        print(f"⚠️ [unified_config] 解析数据源配置失败: {e}, 配置: {ds_config}")
                        continue

                # 按优先级排序（数字越大优先级越高）
                result.sort(key=lambda x: x.priority, reverse=True)
                return result
            else:
                print("⚠️ [unified_config] 数据库中没有数据源配置，使用硬编码配置")
        except Exception as e:
            print(f"⚠️ [unified_config] 从数据库读取数据源配置失败: {e}，使用硬编码配置")

        # 🔥 回退到硬编码配置（兼容性）
        settings = self.get_system_settings()
        data_sources = []

        # AKShare (默认启用)
        akshare_config = DataSourceConfig(
            name="AKShare",
            type=DataSourceType.AKSHARE,
            endpoint="https://akshare.akfamily.xyz",
            enabled=True,
            priority=1,
            description="AKShare开源金融数据接口"
        )
        data_sources.append(akshare_config)

        # Tushare (如果有配置)
        if settings.get("tushare_token"):
            tushare_config = DataSourceConfig(
                name="Tushare",
                type=DataSourceType.TUSHARE,
                api_key=settings.get("tushare_token"),
                endpoint="http://api.tushare.pro",
                enabled=True,
                priority=2,
                description="Tushare专业金融数据接口"
            )
            data_sources.append(tushare_config)

        # Finnhub (如果有配置)
        if settings.get("finnhub_api_key"):
            finnhub_config = DataSourceConfig(
                name="Finnhub",
                type=DataSourceType.FINNHUB,
                api_key=settings.get("finnhub_api_key"),
                endpoint="https://finnhub.io/api/v1",
                enabled=True,
                priority=3,
                description="Finnhub股票数据接口"
            )
            data_sources.append(finnhub_config)

        return data_sources
    
    # ==================== 数据库配置管理 ====================
    
    def get_database_configs(self) -> List[DatabaseConfig]:
        """获取数据库配置"""
        configs = []

        from app.core.config import settings
        
        # MongoDB配置
        mongodb_config = DatabaseConfig(
            name="MongoDB主库",
            type=DatabaseType.MONGODB,
            host=os.getenv("MONGODB_HOST", "localhost"),
            port=int(os.getenv("MONGODB_PORT", "27017")),
            database=os.getenv("MONGODB_DATABASE", "") or os.getenv("MONGODB_DATABASE_NAME", "") or settings.MONGO_DB,
            enabled=True,
            description="MongoDB主数据库"
        )
        configs.append(mongodb_config)
        
        # Redis配置
        redis_config = DatabaseConfig(
            name="Redis缓存",
            type=DatabaseType.REDIS,
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            database=os.getenv("REDIS_DB", "0"),
            enabled=True,
            description="Redis缓存数据库"
        )
        configs.append(redis_config)
        
        return configs
    
    # ==================== 统一配置接口 ====================
    
    async def get_unified_system_config(self) -> SystemConfig:
        """获取统一的系统配置"""
        try:
            config = SystemConfig(
                config_name="统一系统配置",
                config_type="unified",
                llm_configs=self.get_llm_configs(),
                default_llm=self.get_default_model(),
                data_source_configs=self.get_data_source_configs(),
                default_data_source="AKShare",
                database_configs=self.get_database_configs(),
                system_settings=self.get_system_settings()
            )
            return config
        except Exception as e:
            print(f"获取统一配置失败: {e}")
            # 返回默认配置
            return SystemConfig(
                config_name="默认配置",
                config_type="default",
                llm_configs=[],
                data_source_configs=[],
                database_configs=[],
                system_settings={}
            )
    
    def sync_to_legacy_format(self, system_config: SystemConfig) -> bool:
        """同步配置到传统格式"""
        try:
            # 同步模型配置
            for llm_config in system_config.llm_configs:
                self.save_llm_config(llm_config)

            # 读取现有的 settings.json
            current_settings = self.get_system_settings()

            # 同步系统设置（保留现有字段，只更新需要的字段）
            settings = current_settings.copy()

            # 映射新字段名到旧字段名
            if "quick_analysis_model" in system_config.system_settings:
                settings["quick_think_llm"] = system_config.system_settings["quick_analysis_model"]
                settings["quick_analysis_model"] = system_config.system_settings["quick_analysis_model"]

            if "deep_analysis_model" in system_config.system_settings:
                settings["deep_think_llm"] = system_config.system_settings["deep_analysis_model"]
                settings["deep_analysis_model"] = system_config.system_settings["deep_analysis_model"]

            if system_config.default_llm:
                settings["default_model"] = system_config.default_llm

            self.save_system_settings(settings)

            return True
        except Exception as e:
            print(f"同步配置到传统格式失败: {e}")
            return False


# 创建全局实例
unified_config = UnifiedConfigManager()
