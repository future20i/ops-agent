# 🚀 Ops-Agent — 多云运维 Agent 驾驶舱

基于 **Streamlit + Terraform + LangChain** 的智能基础设施即代码 (IaC) 管理平台。

## 架构

```
┌─────────────────────────────────────────┐
│           Streamlit 驾驶舱               │  ← 交互层
├─────────────────────────────────────────┤
│   LangChain Agent → LangGraph 调度      │  ← 大脑 + 任务调度
├─────────────────────────────────────────┤
│        Terraform 执行引擎                │  ← 基础设施抽象层
├─────────────────────────────────────────┤
│   AWS / GCP / Azure                     │  ← 多云适配
└─────────────────────────────────────────┘
```

## 项目结构

```
/ops-agent
├── /app
│   ├── app.py              # Streamlit 入口
│   ├── /agents             # 运维 Agent 逻辑
│   └── /utils              # 辅助工具（CIDR 检查、AWS 包装）
├── /infrastructure
│   ├── /modules/vpc        # VPC Terraform 模块
│   └── /modules/k3s        # K3s 部署模块
├── /data                   # 运维记录与状态
└── requirements.txt        # Python 依赖
```

## 快速启动

```bash
# 1. 克隆项目
git clone https://github.com/future20i/ops-agent.git
cd ops-agent

# 2. 创建虚拟环境
python3 -m venv venv && source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置 AWS 凭证
aws configure
# 或: export AWS_ACCESS_KEY_ID=xxx AWS_SECRET_ACCESS_KEY=xxx

# 5. 启动驾驶舱
streamlit run app/app.py --server.port 8501
```

## 开发里程碑

- [x] **第一阶段**：连接与感知 — VPC 资产列表 + 模拟部署
- [ ] **第二阶段**：IaC 执行引擎 — Terraform apply 集成
- [ ] **第三阶段**：智能治理 — OPA 策略 + LLM 错误分析

## 治理规则

| 资源 | 规则 | 动作 |
|------|------|------|
| VPC | CIDR 重叠保护 | 部署前校验 |
| EC2 | 禁止 SSH 22 | 强制 SSM |
| S3 | 强制加密 | Terraform 检查 |
| IAM | 最小权限 | Role 白名单 |
