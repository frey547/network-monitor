# 轻舟智航 — 量产交付版本集成和管理实习生 面试押题手册

> 基于 network-monitor 项目实战经验，精准对标 JD 五大模块逐一押题。
> 策略：每题先给"标准答案骨架"，再附"本项目实战加分点"，形成**理论+落地**双杀。

---

## 目录

- [第一章 版本管理（JD 模块 1）](#第一章-版本管理jd-模块-1)
- [第二章 交付流程优化（JD 模块 2）](#第二章-交付流程优化jd-模块-2)
- [第三章 集成与测试（JD 模块 3）](#第三章-集成与测试jd-模块-3)
- [第四章 工具和流程管理（JD 模块 4）](#第四章-工具和流程管理jd-模块-4)
- [第五章 问题追踪与管理（JD 模块 5）](#第五章-问题追踪与管理jd-模块-5)
- [第六章 高频综合题 / 场景题](#第六章-高频综合题--场景题)
- [第七章 项目讲述模板（自我介绍 / 项目介绍用）](#第七章-项目讲述模板)
- [附录 A 项目架构速查](#附录-a-项目架构速查)
- [附录 B 关键文件速查表](#附录-b-关键文件速查表)

---

## 第一章 版本管理（JD 模块 1）

### Q1: 你在项目中使用什么分支策略？为什么？

**标准答案：**

本项目采用 **Trunk-Based Development（主干开发）** —— 所有提交直接进入 `main` 分支，配合 Jenkins 流水线在每次推送时自动执行 Build → Test → Push → Deploy。

选择这个策略的原因：
1. **团队规模小**（个人项目），不需要 feature branch 带来的合并开销
2. **交付频率高** —— 每次 commit 即触发完整 CI/CD，快速验证
3. **配合自动回滚** —— Deploy 阶段有健康检查 + 自动回滚到上一版本，降低主干直推的风险

**如果是多人团队，我会切换到 Git Flow 或 GitHub Flow：**
- **Git Flow**：适合有明确发布周期的量产交付场景。`develop` 日常集成，`release/*` 冻结发布，`hotfix/*` 紧急修复，`main` 始终是生产可用的。
- **GitHub Flow**：适合持续交付，feature branch + PR + CI 验证后合入 main。

**加分点（对标轻舟智航）：**
> 量产交付场景我会建议 Git Flow，因为车端软件有明确的版本发布节奏（OTA 推送周期），需要 release branch 做版本冻结和回归测试，同时 hotfix 分支支持紧急问题快速修复不影响下一版本的开发。

---

### Q2: Git tag 和 branch 在版本管理中各自的作用？

**答：**

| 概念 | 用途 | 本项目实践 |
|------|------|-----------|
| **Branch** | 开发流，可变的代码线 | `main` 分支承载所有开发，Jenkins 监听 main 触发流水线 |
| **Tag** | 不可变的版本快照 | Jenkins 用 `BUILD_NUMBER` 作为镜像 tag（如 `app:42`），每次构建同时打 `app:latest` 和 `app:${BUILD_NUMBER}` 双标签 |

**关键区别：**
- Tag 是不可变的，适合标记发布版本（v1.0.0, v1.1.0）
- Branch 是可变的，适合开发过程
- 本项目的双标签策略：`latest` 用于部署，`BUILD_NUMBER` 用于回滚（见 Jenkinsfile Deploy 阶段的 `docker tag ${IMAGE_NAME}:${prevBuild} ${IMAGE_NAME}:latest`）

---

### Q3: 如何保证版本的一致性和可追溯性？

**答：**

本项目通过三层机制保证：

**第一层：镜像版本号 = Jenkins BUILD_NUMBER**
```groovy
// Jenkinsfile
sh "docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} -t ${IMAGE_NAME}:latest ."
```
每次构建产出唯一版本号的镜像，推送到 Harbor 后永久保留。可以随时 `docker pull app:42` 回到任意历史版本。

**第二层：Git commit hash 关联**
Jenkins BUILD_NUMBER 与触发它的 Git commit 一一对应，在 Jenkins 控制台可以追溯"第 42 次构建对应哪个 commit"。

**第三层：Harbor 镜像仓库**
所有版本镜像存储在 Harbor（`192.168.207.129:8088/network-monitor/app`），Harbor 提供镜像扫描、访问控制、操作审计。

**加分点：**
> 生产环境中我还会在 Docker image 的 LABEL 里嵌入 git commit hash 和构建时间：
> ```dockerfile
> LABEL git.commit=${GIT_COMMIT} build.time=${BUILD_TIMESTAMP}
> ```
> 这样 `docker inspect` 就能直接追溯到源码版本。

---

### Q4: 什么是语义化版本（Semantic Versioning）？量产交付中怎么用？

**答：**

格式：`MAJOR.MINOR.PATCH`（如 v2.1.3）

| 位 | 含义 | 何时递增 |
|---|------|---------|
| MAJOR | 不兼容的 API 变更 | 架构重构、协议变更 |
| MINOR | 向后兼容的新功能 | 新增检测算法、新告警类型 |
| PATCH | 向后兼容的 Bug 修复 | 修复 SQLite 并发、内存泄漏 |

**本项目 commit 历史就是活教材：**
- `ca9da21 修复SQLite并发写入、alerts_cache泄漏` → PATCH（bug fix）
- `5555150 feat: add alertmanager + feishu alert system` → MINOR（新功能）
- `9e89fcf feat: production CI/CD pipeline` → MINOR（新能力）

**对标量产交付：**
> 车端 OTA 场景下，MAJOR 版本变更意味着需要全量回归测试；PATCH 版本变更可以走快速验证通道。版本号策略直接影响测试资源分配和发布审批流程。

---

### Q5: 如何处理版本回滚？

**答：**

本项目实现了 **自动回滚机制**（Jenkinsfile Deploy 阶段）：

```groovy
// 1. 部署新版本
docker compose -f docker-compose.deploy.yml up -d network-monitor

// 2. 等待 20 秒，检查健康状态
def health = sh(
    script: "docker inspect --format='{{.State.Health.Status}}' network-monitor",
    returnStdout: true
).trim()

// 3. 不健康 → 自动回滚
if (health != 'healthy') {
    // 把上一版本的镜像 tag 为 latest
    docker tag ${IMAGE_NAME}:${prevBuild} ${IMAGE_NAME}:latest
    // 重新部署
    docker compose -f docker-compose.deploy.yml up -d network-monitor
    // 验证回滚是否成功
    if (rollbackHealth != 'healthy') {
        error "Rollback also failed. Manual intervention required."
    }
}
```

**设计要点：**
1. 健康检查不用 `curl localhost`（Jenkins 容器网络隔离），改用 `docker inspect` 直接读容器状态
2. 回滚后也要做健康检查——"回滚也可能失败"
3. 回滚失败时 `error` 中断流水线，触发人工介入

---

## 第二章 交付流程优化（JD 模块 2）

### Q6: 描述你项目的完整交付流程。

**答：**

```
开发者 push 到 main
    ↓
Jenkins 检测到变更，触发 Pipeline
    ↓
┌─ Stage 1: Checkout ─────────────────────────┐
│  git clone --depth 1 --branch main（浅克隆） │
└─────────────────────────────────────────────┘
    ↓
┌─ Stage 2: Build ────────────────────────────┐
│  docker build → 双 tag: BUILD_NUMBER+latest  │
└─────────────────────────────────────────────┘
    ↓
┌─ Stage 3: Test ─────────────────────────────┐
│  启动容器 → 重试健康检查(60s) → 清理容器     │
└─────────────────────────────────────────────┘
    ↓
┌─ Stage 4: Push Harbor ──────────────────────┐
│  docker login → push 双 tag 到私有仓库       │
└─────────────────────────────────────────────┘
    ↓
┌─ Stage 5: Deploy ───────────────────────────┐
│  pull latest → docker compose up             │
│  → 健康检查 → 失败则自动回滚                  │
└─────────────────────────────────────────────┘
    ↓
生产运行中
    ↓
Prometheus 每 5s 抓取 /metrics
    ↓
触发告警规则 → Alertmanager → /webhook/alert
    ↓
规则引擎 → AI 增强 → 飞书卡片通知
```

---

### Q7: 你在交付流程中遇到过什么问题？怎么解决的？

**答（结合真实 commit 历史，每个都是血泪教训）：**

**问题 1：Jenkins Git 拉取超时（>10 分钟）**
- 原因：Jenkins Git Plugin 的 lightweight checkout 在国内网络下 SSH fetch 极慢
- 解决：`skipDefaultCheckout()` + 手动 `git clone --depth 1`（浅克隆）
- Commit: `e861d90 fix: use shallow clone, skip default checkout`

**问题 2：Test 阶段健康检查立即失败**
- 原因：容器启动需要时间，第一次 curl 时 uvicorn 还没就绪
- 解决：重试循环——30 次 x 2 秒间隔 = 最多等 60 秒
- Commit: `6f8a967 fix: retry health check in Test stage up to 60s`

**问题 3：Deploy 阶段 curl localhost 连不上**
- 原因：Jenkins 运行在 Docker 容器中，`localhost` 是 Jenkins 容器自身，不是宿主机
- 解决：改用 `docker inspect --format='{{.State.Health.Status}}'` 直接检查目标容器
- Commit: `7eddc48 fix: use docker inspect for deploy health check`

**问题 4：Jenkins SSH key 不兼容**
- 原因：Jenkins Git Plugin 的 SSH credential 与 OpenSSH 10.0 的密钥格式不兼容
- 解决：绕过 Jenkins Credential，直接把 SSH key 放到 Jenkins 容器的 `~/.ssh/` 中
- Commit: `7950c8b fix: use container SSH key for GitHub checkout`

**答题策略：** 每个问题都有对应的 commit hash，展示"问题→分析→修复→验证"的闭环能力。

---

### Q8: 如何确保交付物符合质量标准？

**答：**

本项目的质量门禁有四层：

| 层级 | 机制 | 拦截什么 |
|------|------|---------|
| **代码层** | 47 个自动化测试（pytest） | 逻辑 Bug、回归问题 |
| **构建层** | Docker build 成功 | 依赖缺失、语法错误 |
| **运行层** | 容器健康检查（/health + 重试） | 启动失败、运行时崩溃 |
| **部署层** | 生产健康检查 + 自动回滚 | 部署异常、配置错误 |

任何一层失败，流水线中断，不会推进到下一步。

---

## 第三章 集成与测试（JD 模块 3）

### Q9: 你如何做多模块代码的版本集成？

**答：**

本项目有 8 个模块需要集成：

```
collectors/ → detectors/ → engine/ → notify/
    ↑           ↑           ↑         ↑
  services/   models/    knowledge/   ai/
```

**集成策略：**

1. **统一入口** —— `app/main.py` 的 `lifespan()` 函数负责按依赖顺序初始化所有组件，注入到 `app.state`

2. **接口抽象** —— 通过抽象基类解耦模块：
   - `Repository`（抽象） → `SQLiteRepository` / `InMemoryRepository`
   - `Detector`（抽象） → `AnomalyDetector`（Z-Score） / `ThresholdDetector`
   
3. **分层测试验证集成**：
   - 单元测试：各模块独立测试（test_rule_engine, test_ai）
   - 集成测试：`test_webhook.py` 测试完整链路（webhook → RuleEngine → Enricher → Feishu mock）
   - 并发测试：`test_sqlite_concurrency.py` 验证存储层多线程安全

---

### Q10: 遇到过什么集成冲突？怎么解决？

**答：**

**典型案例：飞书通知集成后"静默失败"**

现象：API 返回 `{"status": "ok"}`，但飞书收不到消息。

根因分析（排查了 4 层）：

| 层 | Bug | 影响 |
|----|-----|------|
| **配置层** | `FEISHU_WEBHOOK_URL` 在模块 import 时就被冻结，运行时环境变量变更不生效 | URL 永久为空 |
| **协议层** | 只检查了 HTTP 200，但飞书 API 在 HTTP 200 下也会返回 `{"code": 19001, "msg": "param invalid"}` | 错误被当成功 |
| **异常层** | `except Exception as exc: logger.error(...)` 没有打 traceback | 排查时看不到堆栈 |
| **接口层** | `feishu.send()` 返回 `bool`，但 webhook 路由忽略了返回值 | 失败完全不可见 |

修复：
1. 改为运行时读取 `os.getenv("FEISHU_WEBHOOK_URL")`
2. 解析飞书响应 JSON，校验 `code == 0`
3. 用 `logger.exception()` 保留完整 traceback
4. webhook 路由记录 `notify_ok` / `notify_fail` 计数并返回

**关键教训：** 集成问题往往不是单点故障，而是多层防御全部缺失的结果。

---

### Q11: 你的测试策略是什么？覆盖了哪些维度？

**答：**

```
测试金字塔：

            ┌──────────┐
            │ 集成测试  │  test_webhook.py（8 个用例）
            │          │  完整链路: HTTP → 解析 → 规则 → Enricher → Feishu mock
            ├──────────┤
            │ 单元测试  │  test_rule_engine.py（22 个）
            │          │  test_ai.py（8 个）
            │          │  test_feishu.py（7 个）
            ├──────────┤
            │ 基础设施  │  test_sqlite_concurrency.py（2 个）
            │ 压力测试  │  8 线程 × 50 写入 = 400 并发写入零失败
            └──────────┘
```

| 维度 | 用例数 | 覆盖内容 |
|------|--------|---------|
| **分类准确性** | 11 | 19 种告警名称 → 正确分类（CPU/Memory/Disk/PodCrash/Network/Unknown） |
| **严重度判定** | 5 | 阈值边界：95→CRITICAL、85→WARNING、50→INFO、None→WARNING、"95%"→CRITICAL |
| **AI 降级** | 4 | AI 禁用/启用、Unknown 触发、Critical 触发、Warning 跳过 |
| **AI 容错** | 4 | JSON 解析、Markdown 代码块剥离、畸形 JSON 兜底、API 超时兜底 |
| **飞书协议** | 7 | 卡片结构、严重度颜色映射、发送成功/失败/无 URL |
| **Webhook 集成** | 8 | 空告警、单告警、批量告警、未知告警、值类型强转 |
| **并发安全** | 2 | 纯写并发、读写混合并发 |

---

### Q12: 什么是 Z-Score 异常检测？你怎么用的？

**答：**

**原理：** Z-Score = (当前值 - 均值) / 标准差。衡量当前值偏离历史均值多少个标准差。

**本项目实现（`app/detectors/zscore.py`）：**
```
滑动窗口 = 50 个采样点
异常阈值 = |Z| > 3.0（即偏离均值 3 个标准差）
预热期 = 前 10 个点不做检测（数据不足）
```

**为什么选 Z-Score + Threshold 双检测器？**

| 检测器 | 优势 | 劣势 |
|--------|------|------|
| Z-Score | 自适应基线，能检测渐变异常 | 需要预热期；如果数据一直异常，基线会漂移 |
| Threshold | 简单直接，无预热期 | 硬编码阈值，不适应负载变化 |

本项目对 CPU 指标同时跑两个检测器，如果 Threshold 检测到异常，优先采信（因为 CPU > 80% 就是有问题的，不需要统计推断）。

---

## 第四章 工具和流程管理（JD 模块 4）

### Q13: 你用过哪些 CI/CD 工具？Jenkins 和 GitLab CI 有什么区别？

**答：**

本项目使用 **Jenkins**，原因是需要与私有 Harbor 镜像仓库深度集成，且 Jenkins 对 Docker-in-Docker 场景支持成熟。

| 维度 | Jenkins | GitLab CI |
|------|---------|-----------|
| 配置方式 | `Jenkinsfile`（Groovy DSL） | `.gitlab-ci.yml`（YAML） |
| 运行环境 | 自建 Agent（本项目挂载 docker.sock） | GitLab Runner（Shell/Docker/K8s） |
| 灵活性 | 极高（Groovy 脚本可以写任意逻辑） | 中等（YAML 声明式，复杂逻辑受限） |
| 上手难度 | 高（需要理解 Groovy、Pipeline 语法） | 低（YAML 直观） |
| 生态 | 插件丰富（但质量参差不齐） | 内置集成好（与 GitLab 无缝） |

**本项目 Jenkins Pipeline 特色设计：**
- `skipDefaultCheckout()` —— 绕过 Git Plugin 的慢速 checkout
- `disableConcurrentBuilds()` —— 避免两次部署同时执行
- `timeout(time: 15, unit: 'MINUTES')` —— 全局超时保护
- `buildDiscarder(logRotator(numToKeepStr: '10'))` —— 自动清理旧构建

---

### Q14: 解释 Docker 多阶段构建和镜像优化。

**答：**

本项目的 Dockerfile 虽然不是多阶段构建，但应用了关键优化：

```dockerfile
FROM docker.1ms.run/python:3.12-slim    # slim 基础镜像（非 full，省 ~500MB）
COPY requirements.txt .                  # 先复制依赖清单
RUN pip install --no-cache-dir ...       # 利用 Docker 层缓存
COPY app/ ./app/                         # 最后复制代码（代码变更不会重新安装依赖）
```

**层缓存策略：**
- `requirements.txt` 放在 `app/` 之前 COPY —— 只有依赖变更才重新 `pip install`
- `--no-cache-dir` —— 不缓存 pip 下载包，减小镜像体积
- `apt-get install -y curl && rm -rf /var/lib/apt/lists/*` —— 安装 curl 后清理 apt 缓存

**如果要进一步优化（面试加分）：**
```dockerfile
# 多阶段构建
FROM python:3.12-slim AS builder
RUN pip install --no-cache-dir -r requirements.txt --target=/deps

FROM python:3.12-slim
COPY --from=builder /deps /usr/local/lib/python3.12/site-packages
COPY app/ ./app/
```
这样最终镜像不包含 pip、编译工具等构建时依赖。

---

### Q15: 什么是 Harbor？和 Docker Hub 有什么区别？

**答：**

Harbor 是 VMware 开源的企业级私有镜像仓库。

| 维度 | Harbor | Docker Hub |
|------|--------|------------|
| 部署位置 | 自建（本项目：192.168.207.129:8088） | 云端 SaaS |
| 安全性 | 镜像漏洞扫描、RBAC、审计日志 | 基础（付费版有扫描） |
| 网络 | 内网传输，速度快 | 国内受 GFW 影响，拉取慢 |
| 适用场景 | 企业私有部署、量产交付 | 开源项目、个人使用 |

**本项目实践：**
- Jenkins 构建后推送到 Harbor，部署时从 Harbor 拉取
- 使用 HTTP（非 HTTPS），需要在 Docker daemon 配置 `insecure-registries`
- Harbor 保存所有历史版本，支持任意版本回滚

---

### Q16: 你写过什么自动化脚本？

**答：**

**1. Jenkins Pipeline 脚本（Groovy + Shell）**
- 自动健康检查重试（Shell 循环 + curl）
- 自动回滚逻辑（Groovy 条件判断 + docker tag/compose）

**2. Python 自动化**
- SQLite 并发压力测试（`tests/test_sqlite_concurrency.py`）—— 8 线程 400 写入验证 WAL 模式
- 告警处理自动化 —— 规则引擎自动分类 + AI 增强 + 飞书推送，整条链路零人工

**3. Docker Compose 编排**
- 开发环境（`docker-compose.yml`）：本地构建 + Prometheus + Alertmanager
- 生产环境（`docker-compose.deploy.yml`）：Harbor 拉取 + 健康检查 + 自动重启

---

### Q17: 解释 Docker Compose 中 healthcheck 的配置。

**答：**

```yaml
# docker-compose.deploy.yml
healthcheck:
  test: ["CMD", "curl", "-f", "http://127.0.0.1:8000/health"]
  interval: 10s        # 每 10 秒检查一次
  timeout: 5s          # 单次检查超时
  retries: 3           # 连续 3 次失败才标记 unhealthy
  start_period: 15s    # 启动后 15 秒内的失败不计入
```

**为什么 start_period 很重要？**
容器启动时 uvicorn 需要几秒初始化。没有 start_period 的话，启动期间的失败会被计入 retries，可能导致容器被误判为 unhealthy。

**Jenkins 如何利用它？**
Deploy 阶段用 `docker inspect --format='{{.State.Health.Status}}'` 读取这个状态，而不是自己再跑 curl —— 复用 Docker 的健康检查能力。

---

## 第五章 问题追踪与管理（JD 模块 5）

### Q18: 你如何追踪和管理缺陷？

**答：**

本项目的缺陷管理体现在三个层面：

**1. 代码层 —— 结构化告警追踪**
```python
# app/services/alerting.py — 告警去重 + 频率控制
class AlertManager:
    def add_alert(self, metric, result) -> bool:
        # 去重窗口：5 秒内同一指标只告警一次
        # 频率限制：每分钟最多 2 次
        # 线程安全：threading.Lock
```

**2. 应用层 —— 告警历史记录**
```python
# app/knowledge/history.py
class AlertHistory:
    # 记录最近 1000 条告警
    # 30 分钟窗口计数 → 频繁告警自动加提示
    # "过去30分钟内该告警已触发 N 次，建议排查持续性根因"
```

**3. 运维层 —— 告警生命周期**
```
告警产生 → Event(status="open")
    → 运维响应 → PATCH /events/{id}?status=resolved
    → 闭环
```

**加分点：**
> 实际工作中我会结合 Jira/Linear 做缺陷跟踪，每个缺陷关联 Git commit，确保"问题 → 修复 → 验证 → 关闭"全链路可追溯。

---

### Q19: 如何保证交付版本的质量达标？

**答：**

四层质量门禁 + 可观测性 + 自动回滚：

```
┌─────────────────────────────────────────────┐
│              质量门禁体系                      │
├─────────┬───────────────────────────────────┤
│ 第一层  │ 47 个自动化测试 (pytest)            │
│ 第二层  │ Docker build 成功                   │
│ 第三层  │ 容器健康检查通过（60s 重试窗口）      │
│ 第四层  │ 生产部署后健康检查 + 失败自动回滚     │
├─────────┴───────────────────────────────────┤
│              可观测性                         │
├─────────────────────────────────────────────┤
│ Prometheus 每 5s 采集指标                     │
│ 异常检测（Z-Score + Threshold）               │
│ 告警规则自动触发                              │
│ 飞书实时通知（含排查命令 + AI 建议）            │
├─────────────────────────────────────────────┤
│              自动恢复                         │
├─────────────────────────────────────────────┤
│ docker restart: unless-stopped               │
│ Jenkins Deploy 失败 → 自动回滚上一版本          │
│ 回滚也失败 → error + 人工介入                  │
└─────────────────────────────────────────────┘
```

---

### Q20: 说一个你修复的生产级 Bug。

**答（SQLite 并发写入 — 最佳案例）：**

**现象：** 高负载下 FastAPI 返回 500，日志报 `database is locked`。

**分析：**
- `SimulationService` 后台线程每 2 秒写入 Metric + Anomaly
- FastAPI 请求也会读写数据库
- SQLAlchemy 默认 `QueuePool(pool_size=5)` —— 最多 5 个并发连接
- SQLite 写操作持有文件级锁，多连接并发写 = 必然冲突

**修复（三行核心改动）：**
```python
# 1. WAL 模式：读不阻塞写
cursor.execute("PRAGMA journal_mode=WAL")

# 2. 单连接池：序列化所有写操作
engine = create_engine(..., pool_size=1, max_overflow=0)

# 3. 忙等待超时：30 秒而非默认 5 秒
connect_args={"timeout": 30}
```

**验证：** 8 线程 × 50 写入 = 400 并发写入，零 `database is locked` 错误。

**为什么这是好答案：** 展示了"现象 → 根因定位 → 最小修复 → 压力测试验证"的完整 SRE 问题解决思路。

---

## 第六章 高频综合题 / 场景题

### Q21: 如果生产部署后发现严重 Bug，你怎么处理？

**答：**

**第一步（秒级）：** 本项目 Jenkins Pipeline 自动检测 → 自动回滚到上一版本
```groovy
docker tag ${IMAGE_NAME}:${prevBuild} ${IMAGE_NAME}:latest
docker compose up -d network-monitor
```

**第二步（分钟级）：** 确认回滚成功后，查看失败版本的日志
```bash
docker compose logs --tail=50 network-monitor
```

**第三步（小时级）：** 定位根因 → 修复 → 写测试覆盖 → 重新走 CI/CD

**第四步：** 复盘 —— 为什么测试没有拦住这个 Bug？补充用例。

---

### Q22: 解释 Prometheus + Alertmanager 的工作原理。

**答：**

```
┌─────────────┐  每 5s 拉取 /metrics   ┌────────────┐
│  FastAPI     │ ◄───────────────────── │ Prometheus  │
│  (exporter)  │                        │  (存储+规则) │
└─────────────┘                        └──────┬─────┘
                                              │ 告警规则命中
                                              ▼
                                       ┌────────────┐
                                       │Alertmanager │
                                       │(分组+路由)   │
                                       └──────┬─────┘
                                              │ POST /webhook/alert
                                              ▼
                                       ┌────────────┐
                                       │  FastAPI    │
                                       │(规则+AI+飞书)│
                                       └────────────┘
```

**本项目告警规则：**
```yaml
alert: HighRequestCount
expr: rate(request_count_total[1m]) > 80   # 每秒请求数 > 80
for: 5m                                     # 持续 5 分钟
```

**Alertmanager 配置：**
- `group_wait: 10s` —— 等 10 秒聚合同组告警
- `group_interval: 30s` —— 同一组每 30 秒发送一次
- `repeat_interval: 1m` —— 未恢复的告警每分钟重复发送

**面试延伸问题可能问 pull vs push 模型：**
- Prometheus 是 pull 模型（主动去抓）—— 适合微服务（目标注册即可被发现）
- Push 模型（被监控方主动推）—— 适合短生命周期任务（如 batch job）

---

### Q23: 什么是 Docker-in-Docker？你怎么处理的？

**答：**

本项目 Jenkins 本身运行在 Docker 容器中，但需要在 Pipeline 中执行 `docker build`、`docker push`。

**方案：挂载 docker.sock（Docker-out-of-Docker）**
```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
```

这不是真正的 Docker-in-Docker（DinD），而是让 Jenkins 容器使用宿主机的 Docker daemon。

| 方案 | 优点 | 缺点 |
|------|------|------|
| 挂载 docker.sock | 简单、性能好、共享镜像缓存 | 安全风险（容器可操作宿主机所有容器） |
| 真正 DinD (--privileged) | 完全隔离 | 需要特权模式、性能差、镜像缓存不共享 |
| Kaniko | 无需 Docker daemon | 仅支持构建，不支持 run |

本项目选择 docker.sock 方案是因为单机部署、Jenkins 是受信任的组件。

---

### Q24: 解释你项目中的设计模式。

**答：**

| 设计模式 | 在本项目中的应用 | 文件 |
|----------|----------------|------|
| **Repository 模式** | 抽象存储层，可切换 SQLite/InMemory | `storage/repository.py` |
| **策略模式** | 多种检测算法可插拔（Z-Score, Threshold） | `detectors/` |
| **流水线模式** | 告警处理：分类 → 规则 → AI → 富化 → 通知 | `api/webhook.py` |
| **工厂模式** | 根据 type 创建不同 Collector | `services/simulation.py` |
| **观察者模式** | Prometheus 拉取指标（pull-based 观察） | `core/metrics.py` |
| **优雅降级** | AI 不可用时回退到纯规则引擎 | `ai/analyzer.py` |

---

### Q25: Linux 部署和调试相关问题。

**可能被问到的 Linux 命令（本项目场景）：**

```bash
# 查看容器日志
docker compose logs -f --tail=100 network-monitor

# 进入运行中的容器调试
docker exec -it network-monitor /bin/bash

# 查看容器资源占用
docker stats network-monitor

# 查看端口占用
ss -tlnp | grep 8000
# 或
netstat -tlnp | grep 8000

# 查看进程
ps aux | grep uvicorn

# 查看系统指标（本项目用 psutil 采集的就是这些）
top -bn1 | head -20              # CPU
free -h                           # 内存
df -h                             # 磁盘
iostat -x 1 3                     # IO

# 查看 SQLite WAL 模式是否生效
sqlite3 app.db "PRAGMA journal_mode;"   # 应输出 wal

# 查看 Docker 网络
docker network ls
docker inspect network-monitor --format='{{.NetworkSettings.Networks}}'
```

---

## 第七章 项目讲述模板

### 自我介绍中的项目部分（30 秒版）

> 我做了一个基于 FastAPI 的 AIOps 监控平台。系统通过 Prometheus 采集指标、Z-Score 算法检测异常，触发告警后经过规则引擎分类和 AI 增强分析，最后通过飞书卡片推送给运维人员。CI/CD 方面，我用 Jenkins 搭建了完整的 5 阶段流水线，集成了 Harbor 私有镜像仓库，实现了自动构建、测试、部署和回滚。

### 项目深度介绍（2 分钟版）

> **背景**：为了系统化地学习 DevOps 和 SRE 实践，我从零搭建了一个 AIOps 智能监控平台。
>
> **架构**：FastAPI 后端，Prometheus + Alertmanager 做指标采集和告警路由，SQLite 存储，Docker Compose 编排。
>
> **核心能力**：系统每 2 秒采集系统指标，通过 Z-Score 统计检测和阈值检测两层异常检测。当 Alertmanager 推送告警到我的 webhook 时，规则引擎自动分类告警类型和严重程度，对 Critical 和 Unknown 类型的告警还会调用 AI 做补充分析，最终生成一张包含根因分析、处置建议和排查命令的飞书卡片通知运维。
>
> **CI/CD**：Jenkins 流水线实现 Checkout → Build → Test → Push Harbor → Deploy 全链路。Deploy 阶段有健康检查和自动回滚机制，如果新版本不健康，自动回退到上一版本。
>
> **挑战**：过程中解决了多个生产级问题。比如 SQLite 在多线程下的 `database is locked` 错误，我通过启用 WAL 模式 + 单连接池序列化写入解决，并写了 8 线程并发压力测试验证。再比如飞书通知的"静默失败"问题，根因是飞书 API 在 HTTP 200 下返回错误码，但代码只检查了 HTTP 状态码，我加了响应体校验和结构化日志。
>
> **成果**：47 个自动化测试全部通过，整个系统从代码推送到生产部署全自动，具备异常检测、智能告警、自动回滚能力。

---

## 附录 A 项目架构速查

```
                          ┌──────────────┐
                          │  GitHub Repo │
                          └──────┬───────┘
                                 │ git push
                          ┌──────▼───────┐
                          │   Jenkins     │
                          │  5-Stage CI   │
                          └──────┬───────┘
                                 │ docker push
                          ┌──────▼───────┐
                          │    Harbor     │
                          │  镜像仓库     │
                          └──────┬───────┘
                                 │ docker pull
                   ┌─────────────▼──────────────┐
                   │    Docker Compose 集群       │
                   │                              │
                   │  ┌──────────────────────┐   │
                   │  │   network-monitor     │   │
                   │  │   (FastAPI :8000)     │   │
                   │  │                       │   │
                   │  │  ┌─ collectors ──┐    │   │
                   │  │  │ cpu, mem, disk│    │   │
                   │  │  └───────┬───────┘    │   │
                   │  │          ▼             │   │
                   │  │  ┌─ detectors ──┐     │   │
                   │  │  │ zscore+thresh│     │   │
                   │  │  └───────┬───────┘    │   │
                   │  │          ▼             │   │
                   │  │  ┌─ rule engine ┐     │   │
                   │  │  │ classify+sev │     │   │
                   │  │  └───────┬───────┘    │   │
                   │  │          ▼             │   │
                   │  │  ┌─ AI analyzer ┐     │   │
                   │  │  │ DeepSeek API │     │   │
                   │  │  └───────┬───────┘    │   │
                   │  │          ▼             │   │
                   │  │  ┌─ enricher ───┐     │   │
                   │  │  │ history+merge│     │   │
                   │  │  └───────┬───────┘    │   │
                   │  │          ▼             │   │
                   │  │  ┌─ feishu ─────┐     │   │
                   │  │  │ 卡片通知      │     │   │
                   │  │  └──────────────┘     │   │
                   │  └──────────────────────┘   │
                   │                              │
                   │  ┌─────────────┐             │
                   │  │ Prometheus  │──scrape──►  │
                   │  └──────┬──────┘             │
                   │         ▼                    │
                   │  ┌──────────────┐            │
                   │  │ Alertmanager │──webhook──►│
                   │  └──────────────┘            │
                   └──────────────────────────────┘
```

---

## 附录 B 关键文件速查表

| 文件 | 面试考点 |
|------|---------|
| `Jenkinsfile` | CI/CD 五阶段、自动回滚、skipDefaultCheckout、disableConcurrentBuilds |
| `Dockerfile` | slim 基础镜像、层缓存优化、--no-cache-dir |
| `docker-compose.deploy.yml` | healthcheck 配置、start_period、Harbor 拉取 |
| `app/storage/database.py` | WAL 模式、QueuePool(1)、check_same_thread、pool_pre_ping |
| `app/services/alerting.py` | 内存泄漏修复、threading.Lock、时间窗口去重 |
| `app/notify/feishu.py` | 飞书 API code==0 校验、logger.exception、响应体日志 |
| `app/api/webhook.py` | 告警处理全链路、notify_ok/fail 计数、返回 partial 状态 |
| `app/detectors/zscore.py` | Z-Score 原理、滑动窗口、预热期、std==0 处理 |
| `app/engine/rule_engine.py` | 分类器 + 严重度阈值 + unknown 兜底 |
| `app/ai/analyzer.py` | 降级策略、JSON 解析容错、Markdown 剥离 |
| `tests/test_sqlite_concurrency.py` | 并发压力测试、8 线程 400 写入零失败 |
| `prometheus.yml` | pull 模型、scrape_interval、alertmanager 集成 |
| `alertmanager.yml` | group_wait/interval/repeat_interval 含义 |

---

> **最后提醒：** 面试时不要背答案，用"当时遇到了什么 → 我怎么分析的 → 最终怎么解决的 → 学到了什么"的 STAR 框架讲故事。每个答案末尾可以主动延伸一句"如果是量产交付场景，我会考虑..."来展示你对岗位的理解。
