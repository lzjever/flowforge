# Routilux ⚡

[![PyPI version](https://img.shields.io/pypi/v/routilux.svg)](https://pypi.org/project/routilux/)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![CI](https://github.com/lzjever/routilux/workflows/CI/badge.svg)](https://github.com/lzjever/routilux/actions)

**[English](README.md)**

**Routilux** — 事件驱动的工作流编排框架。流水线一多就难管？用事件队列把编排、并发、断点续跑都管起来，几分钟搭好、随时可恢复。

## ✨ 为什么选 Routilux？

- 🚀 **事件队列**：非阻塞、统一模型，顺序/并发一套 API
- 🔗 **灵活连线**：Routine 多对多、智能路由
- 📊 **状态内置**：执行状态、指标、历史开箱即用
- 🛡️ **错误策略**：STOP / CONTINUE / RETRY / SKIP，自动恢复
- ⚡ **并发执行**：I/O 自动并行，不堵主流程
- 💾 **断点续跑**：任意节点保存/恢复，不怕中断
- 🎯 **生产可用**：错误处理、追踪、监控齐全
- 🎨 **API 简单**：流自动识别，多数场景少传参

## 🎯 适用场景

- **数据流水线**：ETL、数据转换与清洗
- **API 编排**：多接口依赖与协调
- **事件处理**：实时流与响应式系统
- **流程自动化**：业务流程与任务调度
- **微服务协调**：服务间调用与编排
- **LLM 工作流**：AI Agent 编排与链式调用

## 📦 安装与使用

安装、CLI、快速开始与完整文档请见 **[README（英文）](README.md)**。

```bash
# 一行安装（Mac / Linux）
curl -fsSL https://raw.githubusercontent.com/lzjever/routilux/main/install.sh | bash

# 或使用 pipx 安装 CLI
pipx install "routilux[cli]"
routilux run workflow.yaml
```

## 📚 文档与链接

- **文档**：[routilux.readthedocs.io](https://routilux.readthedocs.io)
- **PyPI**：[pypi.org/project/routilux](https://pypi.org/project/routilux)
- **GitHub**：[github.com/lzjever/routilux](https://github.com/lzjever/routilux)

## 📄 许可

Apache 2.0，详见 [LICENSE](LICENSE)。
