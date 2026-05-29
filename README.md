# 🚀 Ops-Agent — 多云运维 Agent 平台

基于 **Streamlit + Terraform + LLM** 的智能基础设施即代码 (IaC) 管理平台。

> 📍 当前阶段：**MVP v0.3** — Streamlit 驾驶舱 + Terraform 引擎 + 智能治理  
> 🗺️ 演进方向：FastAPI + 多云抽象层（详见 [迁移路线图](docs/plans/migration-mvp-to-fastapi.md)）

---

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│              Streamlit 驾驶舱（当前）→ FastAPI（目标）     │  ← 交互层
├─────────────────────────────────────────────────────────┤
│      治理引擎（6 规则）  +  LLM 错误顾问                  │  ← 智能决策层
├─────────────────────────────────────────────────────────┤
│            Terraform 执行引擎（plan/apply/destroy）       │  ← IaC 抽象层
├─────────────────────────────────────────────────────────┤
│   AWS (boto3)         → 阿里云 / 腾讯云（规划中）         │  ← 多云适配
└─────────────────────────────────────────────────────────┘
```

### 核心闭环

```
用户操作 → 治理策略检查 → Terraform Plan → 人工确认 → Terraform Apply
                ↓ 违规                         ↓ 失败
          LLM 解释 + 拦截                  LLM 诊断 + 建议
```

---

## 项目结构

```
/ops-agent
├── /app
│   ├── app.py                        # Streamlit 驾驶舱入口
│   ├── /agents                       # 智能治理层
│   │   ├── governance.py             #   策略引擎（6 条规则）
│   │   ├── llm_advisor.py            #   LLM 错误顾问（离线可用）
│   │   ├── k3s_agent.py              #   K3S 一键部署引擎
│   │   └── vpc_agent.py              #   VPC Agent 模板
│   └── /utils                        # 工具层
│       ├── aws_client.py             #   boto3 客户端包装
│       ├── network.py                #   CIDR 防冲突引擎
│       └── terraform_executor.py     #   Terraform CLI 封装
├── /infrastructure                   # IaC 模板
│   └── /modules
│       ├── /vpc                      #   VPC Terraform 模块
│       └── /k3s                      #   K3S 部署模块
├── /docs/plans                       # 开发计划与路线图
│   ├── 2026-05-29-phase2-terraform-engine.md
│   ├── 2026-05-29-phase3-governance-llm.md
│   └── migration-mvp-to-fastapi.md
├── /data                             # 运维记录
├── requirements.txt
└── README.md
```

---

## 开发里程碑

### ✅ 第一阶段：连接与感知
- Streamlit 资产仪表盘
- VPC 列表（模拟 + 真实 boto3 双模式）
- CIDR 网络地址计算

### ✅ 第二阶段：IaC 执行引擎
- `terraform_executor.py`：完整 plan/apply/destroy 封装
- Terraform 模式切换（🧪 模拟 / 🏗️ Terraform）
- 动态生成 `terraform.tfvars`
- Terraform plan/apply 输出实时展示

### ✅ 第三阶段：智能治理与反馈
- 6 条治理规则：CIDR / SSH / S3 / IAM / DNS / Tags
- Block/Warn 分级拦截
- LLM 错误顾问：分析违规 + Terraform 错误
- 离线 fallback（无需 API Key 可用）

### 🔲 第四阶段：迁移到 FastAPI 多云平台
- 详见 [迁移路线图](docs/plans/migration-mvp-to-fastapi.md)
- FastAPI 入口 + API 路由
- 多云抽象层（`ICloudProvider` 接口）
- VPS 管理器 + 异步 SSH 执行器

---

## 快速启动

```bash
# 1. 克隆项目
git clone https://github.com/future20i/ops-agent.git
cd ops-agent

# 2. 创建虚拟环境
python3 -m venv venv && source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. （可选）配置 AWS 凭证 — 不配置也能用模拟模式
aws configure
# 或: export AWS_ACCESS_KEY_ID=xxx AWS_SECRET_ACCESS_KEY=xxx

# 5. （可选）配置 LLM API Key — 不配置也能用离线建议
export OPENAI_API_KEY=sk-xxx

# 6. 启动驾驶舱
streamlit run app/app.py --server.port 8501
```

---

## 治理规则清单

| 资源 | 规则 | 级别 | 动作 |
|------|------|:--:|------|
| VPC | CIDR 重叠保护 | 🚫 block | 部署前校验，冲突则拦截 |
| VPC | DNS 支持检查 | ⚠️ warn | 提示建议启用 |
| EC2 | 禁止开放 SSH 22 | 🚫 block | 强制 SSM Session Manager |
| S3 | 强制服务端加密 | 🚫 block | Terraform 配置检查 |
| IAM | 最小权限原则 | ⚠️ warn | Role 权限审计 |
| Global | Environment/ManagedBy 标签 | ⚠️ warn | 成本追踪与资源管理 |

---

## 目标架构（FastAPI 多云平台）

当前 MVP 使用 Streamlit 作为交互层。演进目标架构如下：

```
┌──────────────────────────────────────────────┐
│         FastAPI REST API (目标)               │
│  POST /api/v1/task  ← 自然语言运维指令        │
├──────────────────────────────────────────────┤
│         Ops Agent 核心引擎                     │
│  ┌──────────┬──────────┬──────────────────┐  │
│  │ 任务解析  │ 工作流编排 │ 权限验证 + 审计   │  │
│  └──────────┴──────────┴──────────────────┘  │
├──────────────────────────────────────────────┤
│         多云抽象层 (ICloudProvider)            │
│  ┌──────────┬──────────┬──────────────────┐  │
│  │ AWS      │ 阿里云    │ 腾讯云            │  │
│  │ (boto3)  │ (alibaba) │ (tencentcloud)   │  │
│  └──────────┴──────────┴──────────────────┘  │
├──────────────────────────────────────────────┤
│         执行层                                 │
│  ┌──────────┬──────────┬──────────────────┐  │
│  │ SSH/     │ K3S 编排  │ Terraform IaC    │  │
│  │ Ansible  │          │                  │  │
│  └──────────┴──────────┴──────────────────┘  │
└──────────────────────────────────────────────┘
```

### 核心模块设计

- **`ICloudProvider`** — 统一多云接口：`describe_instances` / `create_instance` / `delete_instance` / `configure_security_group`
- **`VPSManager`** — VPS 集群全生命周期：创建网络 → 实例 → 安全组 → 弹性IP
- **`SSHExecutor`** — 异步远程命令执行 + 脚本上传
- **`K3SManager`** — K3S 集群搭建：节点准备 → Master 初始化 → Worker 加入 → kubeconfig 导出

---

## 任务示例

```json
{
  "user_query": "在 AWS 北京区域创建一个 3 节点的 K3S 集群，实例类型 t3.medium"
}
```

```
┌─────────────────────────────────────────────┐
│ 1. 🔧 系统环境准备（swap/内核/sysctl）        │
│ 2. 🖥️ 创建 3 个 EC2 实例                     │
│ 3. ⭐ 初始化 Master 节点 → 安装 K3S Server     │
│ 4. 🔗 加入 2 个 Worker 节点                   │
│ 5. ✅ 集群验证 → 导出 kubeconfig              │
└─────────────────────────────────────────────┘
```

---

## 安全设计

| 维度 | 措施 |
|------|------|
| 凭证管理 | 环境变量注入，不硬编码；目标接入 HashiCorp Vault |
| 权限控制 | IAM 最小权限 + 高危操作审批流程（规划中） |
| 审计日志 | 全操作记录（WHO/WHAT/WHEN/WHERE）+ 6 个月留存 |
| 故障恢复 | 幂等性设计 + Terraform state 回滚 |

---

## 技术栈

| 层 | 当前 (MVP) | 目标 |
|----|:----------:|:----:|
| 交互 | Streamlit | FastAPI + Claude API |
| 编排 | Python subprocess | LangChain + LangGraph |
| IaC | Terraform CLI | Terraform + OPA |
| 云 SDK | boto3 (AWS) | AWS + 阿里云 + 腾讯云 |
| 远程 | — | asyncssh + Ansible |
| 存储 | session_state | SQLite → PostgreSQL |
| 部署 | 手动 | Docker Compose |
