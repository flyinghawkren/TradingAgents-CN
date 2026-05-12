from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import os

from app.services.config_service import config_service


class ConfigProvider:
    """Effective configuration provider with simple env→DB merge and TTL cache.

    - Priority: ENV > DB
    - Cache TTL: configurable (default 60s)
    - Invalidate on writes: caller should invoke `invalidate()` after writes
    """

    def __init__(self, ttl_seconds: int = 60) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
        self._cache_settings: Optional[Dict[str, Any]] = None
        self._cache_time: Optional[datetime] = None

    def invalidate(self) -> None:
        self._cache_settings = None
        self._cache_time = None

    def _is_cache_valid(self) -> bool:
        return (
            self._cache_settings is not None
            and self._cache_time is not None
            and __import__("datetime").datetime.now(__import__("datetime").timezone.utc) - self._cache_time < self._ttl
        )

    async def get_effective_system_settings(self) -> Dict[str, Any]:
        if self._is_cache_valid():
            return dict(self._cache_settings or {})

        # Load DB settings
        cfg = await config_service.get_system_config()
        base: Dict[str, Any] = {}
        if cfg and getattr(cfg, "system_settings", None):
            try:
                base = dict(cfg.system_settings)
            except Exception:
                base = {}

        # Merge ENV over DB (best-effort heuristics):
        # - if ENV with exact key exists -> override
        # - try uppercased and dot/space to underscore variants
        merged: Dict[str, Any] = dict(base)
        for k, v in list(base.items()):
            candidates = [
                k,
                k.upper(),
                str(k).replace(".", "_").replace(" ", "_").upper(),
            ]
            found = None
            for ek in candidates:
                if ek in os.environ:
                    found = os.environ.get(ek)
                    break
            if found is not None:
                merged[k] = found

        # 🔧 修正默认模型：如果 quick/deep_analysis_model 缺失或对应模型不可用，自动选择第一个可用模型
        merged = await self._validate_and_fix_default_models(merged, cfg)

        # Cache
        self._cache_settings = dict(merged)
        self._cache_time = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        return dict(merged)

    async def _validate_and_fix_default_models(self, settings: Dict[str, Any], cfg) -> Dict[str, Any]:
        """验证并修正默认模型设置，确保 quick/deep_analysis_model 指向实际可用的模型"""
        result = dict(settings)

        # 获取当前可用的模型列表
        available_models = set()
        if cfg and cfg.llm_configs:
            available_models = {m.model_name for m in cfg.llm_configs if m.enabled}

        # 如果数据库中没有可用模型，尝试从 .env 生成
        if not available_models:
            from app.core.unified_config import unified_config
            env_configs = unified_config.get_llm_configs()
            available_models = {m.model_name for m in env_configs if m.enabled}

        if not available_models:
            print("⚠️ [config_provider] 未找到任何可用模型，跳过默认模型修正")
            return result

        print(f"🔍 [config_provider] 当前可用模型: {available_models}")

        # 检查并修正 quick_analysis_model
        quick_model = result.get("quick_analysis_model", "")
        if not quick_model or quick_model not in available_models:
            first_model = sorted(available_models)[0]
            print(f"   ⚠️ quick_analysis_model='{quick_model}' 不可用，自动修正为 '{first_model}'")
            result["quick_analysis_model"] = first_model
        else:
            print(f"   ✓ quick_analysis_model='{quick_model}' 有效")

        # 检查并修正 deep_analysis_model
        deep_model = result.get("deep_analysis_model", "")
        if not deep_model or deep_model not in available_models:
            first_model = sorted(available_models)[0]
            print(f"   ⚠️ deep_analysis_model='{deep_model}' 不可用，自动修正为 '{first_model}'")
            result["deep_analysis_model"] = first_model
        else:
            print(f"   ✓ deep_analysis_model='{deep_model}' 有效")

        return result
    async def get_system_settings_meta(self) -> Dict[str, Dict[str, Any]]:
        """Return metadata for system settings keys including sensitivity, editability and source.
        Fields per key:
          - sensitive: bool (by keyword patterns)
          - editable: bool (False if sensitive or source is environment; True otherwise)
          - source: 'environment' | 'database' | 'default'
          - has_value: bool (effective value is not None/empty)
        """
        # Load DB settings raw
        cfg = await config_service.get_system_config()
        db_settings: Dict[str, Any] = {}
        if cfg and getattr(cfg, "system_settings", None):
            try:
                db_settings = dict(cfg.system_settings)
            except Exception:
                db_settings = {}

        def _env_override_for_key(key: str) -> Optional[Any]:
            candidates = [
                key,
                key.upper(),
                str(key).replace(".", "_").replace(" ", "_").upper(),
            ]
            for ek in candidates:
                if ek in os.environ:
                    return os.environ.get(ek)
            return None

        sens_patterns = ("key", "secret", "password", "token", "client_secret")
        meta: Dict[str, Dict[str, Any]] = {}
        for k, v in db_settings.items():
            env_v = _env_override_for_key(k)
            source = "environment" if env_v is not None else ("database" if v is not None else "default")
            sensitive = isinstance(k, str) and any(p in k.lower() for p in sens_patterns)
            editable = not sensitive and source != "environment"
            effective_val = env_v if env_v is not None else v
            has_value = effective_val not in (None, "")
            meta[k] = {
                "sensitive": bool(sensitive),
                "editable": bool(editable),
                "source": source,
                "has_value": bool(has_value),
            }
        return meta



# Module-level singleton
provider = ConfigProvider(ttl_seconds=60)

