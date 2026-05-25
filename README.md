# TradingAgents 中文增强版

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/Version-v1.0.1-green.svg)](./VERSION)
[![Documentation](https://img.shields.io/badge/docs-中文文档-green.svg)](./docs/)
[![Original](https://img.shields.io/badge/基于-TauricResearch/TradingAgents-orange.svg)](https://github.com/TauricResearch/TradingAgents)

---

## ⚠️ 重要版权声明与授权说明

当前项目Fork自开源项目📦 GitHub 仓库：https://github.com/hsliuping/TradingAgents-CN，基于该项目进行功能增强，仅用于开源探索，请勿用于任何商业用途。

## 使用指南
1. 安装Docker Desktop
2. 复制项目代码至本地并进入项目目录：
   git clone https://github.com/flyinghawkren/TradingAgents-CN.git
   cd TradingAgents-CN
3. 配置大模型及主要数据源API Key：
   cp .env.docker .env
   vi .env
   修改 DEEPSEEK_ENABLED=true，并输入 DEEPSEEK_API_KEY；
   修改 TUSHARE_ENABLED=true，并输入 TUSHARE_TOKEN
4. 进入项目目录编译打包：docker-compose -f docker-compose.hub.nginx.yml build
5. 启动容器：docker-compose -f docker-compose.hub.nginx.yml up -d
6. 初始化用户，默认用户名/密码：admin/admin123
   docker exec -it tradingagents-backend python scripts/import_config_and_create_user.py
7. 访问服务：http://127.0.0.1/

## 功能开发及演化
可使用OpenCode打开项目目录，调整优化功能
