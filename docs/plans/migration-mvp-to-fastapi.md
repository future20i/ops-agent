# MVP → FastAPI 多云平台 迁移路线图

> **目标:** 将 Streamlit 原型演进为 README 中定义的 FastAPI + 多云抽象层架构

---

## 差距分析

| 维度 | MVP（当前） | 目标（README） | 差距 |
|------|:-----------:|:--------------:|------|
| 交互层 | Streamlit 页面 | FastAPI + Claude API | 需重写 |
| 云抽象 | 仅 AWS boto3 | AWS/阿里云/腾讯云统一接口 | 需新建 |
| VPS 管理 | VPC 列表+创建 | 集群创建/删除/安全组/弹性IP | 需扩展 |
| 远程执行 | 无 | 异步 SSH + Ansible | 需新建 |
| K3S 编排 | Terraform 模板 | Python 驱动全流程 | 需新建 |
| 安全 | 治理规则 (6条) | RBAC/审计/Vault | 需扩展 |
| 部署 | 手动 streamlit run | Docker Compose | 需新建 |

---

## 迁移阶段

### 阶段 A: 基础重构（2-3 天）

**目标:** 建立 FastAPI 骨架 + 多云抽象层

#### Task A1: 创建 FastAPI 入口

**文件:** `app/server.py`（新建）

```python
from fastapi import FastAPI
from app.api.routes import router
from app.core.config import settings

app = FastAPI(title="Ops-Agent", version="0.2.0")
app.include_router(router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok", "version": app.version}
```

#### Task A2: 多云抽象层接口

**文件:** `app/cloud/base.py`（新建，迁移 README 中的 ICloudProvider）

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any

class CloudProvider(str, Enum):
    AWS = "aws"
    ALIYUN = "aliyun"
    TENCENT = "tencent"

@dataclass
class Instance:
    instance_id: str
    instance_name: str
    provider: CloudProvider
    region: str
    instance_type: str
    cpu: int
    memory: int
    status: str
    public_ip: str
    private_ip: str
    os: str
    tags: Dict[str, str]

class ICloudProvider(ABC):
    @abstractmethod
    async def describe_instances(self, region: str, **filters) -> List[Instance]: ...
    @abstractmethod
    async def create_instance(self, config: Dict[str, Any]) -> Instance: ...
    @abstractmethod
    async def delete_instance(self, instance_id: str, region: str) -> bool: ...
    @abstractmethod
    async def reboot_instance(self, instance_id: str, region: str) -> bool: ...
    @abstractmethod
    async def configure_security_group(self, instance_id: str, rules: List[Dict]) -> bool: ...
    @abstractmethod
    async def allocate_elastic_ip(self, instance_id: str) -> str: ...
    @abstractmethod
    async def create_volume(self, size_gb: int, instance_id: str) -> Dict[str, Any]: ...
```

#### Task A3: AWS Provider 实现

**文件:** `app/cloud/providers/aws.py`（新建，迁移 aws_client.py）

#### Task A4: API 路由

**文件:** `app/api/routes.py`, `app/api/schemas.py`（新建）

```
GET  /api/v1/instances  → 列出所有 VPS
POST /api/v1/instances  → 创建 VPS
DELETE /api/v1/instances/{id} → 删除 VPS
POST /api/v1/clusters/k3s → 创建 K3S 集群
POST /api/v1/scripts/run → 执行远程脚本
```

---

### 阶段 B: VPS + 远程执行（3-4 天）

**目标:** 实现完整的 VPS 生命周期管理 + SSH 远程执行

#### Task B1: VPS Manager

**文件:** `app/managers/vps_manager.py`（迁移 README 中的 VPSManager）

- 集群创建（多实例 + 网络 + 安全组 + 弹性IP）
- 集群删除
- 实例重启

#### Task B2: SSH Executor

**文件:** `app/executors/ssh_executor.py`（迁移 README 中的 SSHExecutor）

- 异步远程命令执行
- 文件上传
- 脚本执行

#### Task B3: 安全模块

**文件:** `app/security/auth.py`, `app/security/audit.py`

- API Key 认证
- 操作审计日志（WHO/WHAT/WHEN/WHERE/WHY）
- 高危操作审批流程（预留）

---

### 阶段 C: K3S 编排（3-4 天）

**目标:** Python 驱动的全自动 K3S 集群搭建

#### Task C1: K3S Manager

**文件:** `app/orchestration/k3s_manager.py`（迁移 README 中的 K3SManager）

- 节点系统准备（swap/内核/sysctl）
- 主节点初始化
- 工作节点加入
- kubeconfig 导出
- CNI 部署

---

### 阶段 D: 部署与集成（2 天）

**目标:** Docker 化部署 + 原 Streamlit 作为可选前端

#### Task D1: Docker Compose

**文件:** `docker-compose.yml`, `Dockerfile`

#### Task D2: 保留 Streamlit 作为调试面板

Streamlit 页面保留在 `/debug` 路径，作为可视化辅助工具

#### Task D3: README 更新

合并当前 README 的完整设计方案，与实际代码对齐

---

## 新目录结构

```
/ops-agent
├── /app
│   ├── server.py              # FastAPI 入口（新）
│   ├── /api                    # API 层（新）
│   │   ├── routes.py
│   │   ├── schemas.py
│   │   └── deps.py
│   ├── /cloud                  # 多云抽象层（新）
│   │   ├── base.py             # ICloudProvider 接口
│   │   └── providers/
│   │       └── aws.py          # AWS 实现
│   ├── /managers               # 业务管理（新）
│   │   └── vps_manager.py
│   ├── /executors              # 远程执行（新）
│   │   └── ssh_executor.py
│   ├── /orchestration          # 编排（新）
│   │   └── k3s_manager.py
│   ├── /security               # 安全（新）
│   │   ├── auth.py
│   │   └── audit.py
│   ├── /agents                 # 治理 + LLM（已有）
│   │   ├── governance.py
│   │   ├── llm_advisor.py
│   │   └── vpc_agent.py
│   ├── /utils                  # 工具（已有）
│   │   ├── network.py
│   │   ├── aws_client.py
│   │   └── terraform_executor.py
│   └── app.py                  # Streamlit 前端（保留）
├── /infrastructure             # Terraform（已有）
├── /docker                     # Docker 配置（新）
│   ├── Dockerfile
│   └── docker-compose.yml
├── requirements.txt            # 更新依赖
└── README.md                   # 与代码对齐
```

---

## 依赖更新

```
# requirements.txt 新增
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
asyncssh>=2.14.0
pydantic>=2.5.0
python-jose[cryptography]>=3.3.0
httpx>=0.26.0
```

---

## 风险评估

| 风险 | 概率 | 缓解措施 |
|------|:--:|---------|
| FastAPI 学习曲线 | 低 | 同步写法为主，逐步引入 async |
| 阿里云/腾讯云 SDK 差异 | 中 | 先只实现 AWS，接口设计预留扩展点 |
| SSH 密钥管理 | 中 | 支持环境变量 + 文件路径两种方式 |
| K3S 兼容性 | 低 | 基于已验证的 user_data.sh 脚本 |
