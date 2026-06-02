# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TradingAgents-CN 是一个 AI 驱动的多智能体股票分析和交易系统，基于 LangGraph 构建。核心是多个 AI 分析师（智能体）通过辩论和协作来做出投资决策。

## Architecture

### 核心系统 (`tradingagents/`)
多智能体决策引擎，基于 LangGraph 的有向图：

- **`graph/trading_graph.py`** — 主图编排器，驱动智能体协作流程
- **`graph/setup.py`** — 图结构初始化
- **`graph/propagation.py`** — 前向传播（分析执行）
- **`graph/reflection.py`** — 反思与记忆
- **`graph/conditional_logic.py`** — 条件分支逻辑
- **`graph/signal_processing.py`** — 信号处理
- **`agents/`** — 智能体实现：
  - `analysts/` — 分析师智能体（基本面、技术面、新闻、社交媒体、中国市场）
  - `researchers/` — 研究员（多头/空头研究员）
  - `managers/` — 研究经理
  - `risk_mgmt/` — 风险管理者
  - `trader/` — 交易员
  - `utils/` — 记忆系统、工具包
- **`llm_clients/`** — LLM 客户端抽象层，支持多供应商（OpenAI、DeepSeek、Google、DashScope 等）
- **`llm_adapters/`** — LLM 适配器，将不同供应商 API 统一为兼容接口
- **`dataflows/`** — 数据流层，整合 AKShare、Tushare、BaoStock 等数据源
- **`tools/`** — 智能体工具（分析工具、新闻工具）
- **`config/`** — 配置管理
- **`default_config.py`** — 默认配置，自动根据环境变量选择 LLM 供应商

### FastAPI 后端 (`app/`)
- **`main.py`** — FastAPI 应用入口，注册路由和中间件
- **`__main__.py`** — 支持 `python -m app` 启动，含 UTF-8 编码配置
- **`routers/`** — API 路由（auth, analysis, stocks, screening, queue, scheduler 等~40+ 路由模块）
- **`services/`** — 业务逻辑层
- **`worker/`** — 数据同步任务（Tushare、AKShare 同步服务）
- **`middleware/`** — 中间件（操作日志等）
- **`core/`** — 核心配置、数据库连接、日志配置
- **`models/`**、**`schemas/`** — 数据模型
- **`utils/`** — 工具函数

### Vue 3 前端 (`frontend/`)
Vue 3 + TypeScript + Element Plus + Vite + Pinia + Vue Router + ECharts

- **`src/views/`** — 页面视图（About, Analysis, Auth, Dashboard, Favorites, PaperTrading, Portfolio, Reports, Screening, Settings, SmartInvestment, Stocks, System, Tasks 等）
- **`src/api/`** — API 调用层
- **`src/stores/`** — Pinia 状态管理
- **`src/router/`** — 路由配置
- **`src/components/`** — 通用组件

### Streamlit Web 界面 (`web/`)
替代前端方案，基于 Streamlit

- **`app.py`** — 主应用
- **`run_web.py`** — 启动脚本（含依赖检查、缓存清理）
- **`components/`** — Streamlit 组件
- **`modules/`** — 功能模块（配置管理、数据库管理、token 统计等）
- **`utils/`** — 工具函数

### CLI (`cli/`)
基于 Typer + Rich 的命令行界面

- **`main.py`** — CLI 入口，支持交互式股票分析

### 部署
- **`docker-compose.yml`** — 开发部署（v1.0.0-preview），前后端分离暴露端口
- **`docker-compose.hub.nginx.yml`** — 生产部署（v1.0.1），Docker Hub 镜像 + Nginx 反向代理统一 80 端口
- **`docker-compose.hub.nginx.arm.yml`** — ARM64 生产部署版
- **`Dockerfile.backend`**、**`Dockerfile.frontend`** — 镜像构建文件
- **`nginx/nginx.conf`** — Nginx 配置

## Key Commands

### 安装
```bash
# 方式一：pip（推荐）
pip install -e .

# 方式二：uv（更快）
uv pip install -e .

# 安装可选依赖
pip install -e ".[qianfan]"
```

### 运行后端
```bash
python -m app
# 或
uvicorn app.main:app --reload
```

### 运行前端
```bash
cd frontend && yarn dev      # 开发模式
cd frontend && yarn build    # 生产构建
```

### 运行 Streamlit Web
```bash
python web/run_web.py
```

### 运行 CLI
```bash
python cli/main.py
# 或（安装后）
tradingagents
```

### 测试
```bash
pytest                           # 运行单元测试（默认跳过集成测试）
pytest -m integration            # 运行集成测试
pytest tests/path/to/test.py     # 运行单个测试文件
pytest -k "test_name"            # 运行匹配的测试
```

### Docker 部署
```bash
# 生产部署（推荐）
docker-compose -f docker-compose.hub.nginx.yml up -d

# ARM64 部署
docker-compose -f docker-compose.hub.nginx.arm.yml up -d

# 本地构建镜像
docker-compose -f docker-compose.hub.nginx.yml build

# 初始化用户（首次部署必需）
docker exec -it tradingagents-backend python scripts/import_config_and_create_user.py
```

## Environment

- Python >= 3.10
- Node >= 18.0.0
- MongoDB 4.4+（Docker 或本地）
- Redis 7+（Docker 或本地）
- 配置文件：`.env`（复制自 `.env.example` 或 `.env.docker`），需配置至少一个 AI 模型供应商 API Key（推荐 DeepSeek 或 DashScope）和数据源 Token（Tushare）

## Project Structure Key Points

- 根目录 `main.py` — 核心系统的独立运行入口（直接调用 `TradingAgentsGraph` 进行单次分析）
- `config/` — 日志配置（`logging.toml`、`logging_docker.toml`）
- `scripts/` — 大量实用脚本（数据导入、配置初始化、工具脚本）
- `tests/pytest.ini` — 默认跳过集成测试，`integration` 标记的测试需手动运行
