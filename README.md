# Network Monitor AI OPS Demo

## 项目概述
本项目是一个 Python 网络监控 demo，包含：
- CPU / 内存指标模拟采集
- 异常检测（Z-score）
- 告警管理（去重 + 限流）
- FastAPI API 提供 `/metrics`、`/alerts`、`/simulate` 接口

可作为 AI OPS 原型，后续可迭代升级算法和扩展指标。

## 部署步骤

### 1. 克隆项目并进入目录
```bash
git clone <repo_url>
cd network-monitor/app
