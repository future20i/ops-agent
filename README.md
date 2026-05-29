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



# 多云运维Agent系统 - 完整设计方案

## 系统架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                     Hermes 对话交互界面                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│              Ops Agent 核心引擎 (Python/FastAPI)                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  - 自然语言理解 & 任务解析                               │  │
│  │  - 工作流编排 & 执行管理                                 │  │
│  │  - 权限验证 & 审计日志                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼────────┐ ┌────▼──────────┐ ┌──▼───────────────┐
│  AWS SDK       │ │  阿里云 SDK   │ │  腾讯云 SDK      │
│  (boto3)       │ │  (alibabacloud)│ │  (tencentcloud)  │
└───────┬────────┘ └────┬──────────┘ └──┬───────────────┘
        │                │                │
┌───────▼────────────────▼────────────────▼──────────────┐
│           多云抽象层 (Cloud Provider Interface)        │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │
│  │  VPS/ECS    │  │  Network    │  │  Storage     │  │
│  │  Manager    │  │  Manager    │  │  Manager     │  │
│  └─────────────┘  └─────────────┘  └──────────────┘  │
└────────────────────────┬─────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼────────┐ ┌────▼──────────┐ ┌──▼───────────────┐
│  SSH/Ansible   │ │  Script Mgmt  │ │  Container       │
│  Executor      │ │  (k3s, k8s)   │ │  Registry        │
└────────────────┘ └───────────────┘ └──────────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │  监控 & 日志系统                 │
        │  (Prometheus, ELK, etc.)       │
        └────────────────────────────────┘
```

## 核心模块详解

### 1. 多云抽象层 (Cloud Provider Interface)

**目标**: 统一AWS、阿里云、腾讯云的API差异

```python
# cloud_provider/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any

class CloudProvider(Enum):
    AWS = "aws"
    ALIYUN = "aliyun"
    TENCENT = "tencent"

@dataclass
class Instance:
    """统一实例模型"""
    instance_id: str
    instance_name: str
    provider: CloudProvider
    region: str
    instance_type: str
    cpu: int
    memory: int
    status: str  # running, stopped, terminated
    public_ip: str
    private_ip: str
    os: str  # linux, windows
    tags: Dict[str, str]

class ICloudProvider(ABC):
    """云平台接口基类"""
    
    @abstractmethod
    async def describe_instances(self, region: str, **filters) -> List[Instance]:
        """列出实例"""
        pass
    
    @abstractmethod
    async def create_instance(self, config: Dict[str, Any]) -> Instance:
        """创建VPS实例"""
        pass
    
    @abstractmethod
    async def delete_instance(self, instance_id: str, region: str) -> bool:
        """删除实例"""
        pass
    
    @abstractmethod
    async def reboot_instance(self, instance_id: str, region: str) -> bool:
        """重启实例"""
        pass
    
    @abstractmethod
    async def configure_security_group(self, 
                                      instance_id: str, 
                                      rules: List[Dict]) -> bool:
        """配置防火墙规则"""
        pass
    
    @abstractmethod
    async def allocate_elastic_ip(self, instance_id: str) -> str:
        """分配弹性IP"""
        pass
    
    @abstractmethod
    async def create_volume(self, size_gb: int, 
                          instance_id: str) -> Dict[str, Any]:
        """创建存储卷"""
        pass
```

### 2. VPS管理器

```python
# managers/vps_manager.py
from typing import Optional
import asyncio

class VPSManager:
    """VPS生命周期管理"""
    
    def __init__(self, providers: Dict[CloudProvider, ICloudProvider]):
        self.providers = providers
    
    async def create_vps_cluster(self, config: Dict[str, Any]) -> List[Instance]:
        """
        创建VPS集群
        
        config例子:
        {
            "cluster_name": "k3s-cluster-prod",
            "provider": "aws",  # 或 "aliyun", "tencent"
            "region": "cn-beijing",
            "instance_count": 3,
            "instance_type": "t3.medium",
            "os": "ubuntu-22.04",
            "network": {
                "vpc_cidr": "10.0.0.0/16",
                "subnet_cidr": "10.0.1.0/24"
            },
            "security": {
                "ssh_port": 22,
                "allowed_ips": ["0.0.0.0/0"],
                "key_pair_name": "my-key"
            },
            "storage": {
                "root_volume_size": 50,
                "data_volume_size": 100
            },
            "tags": {
                "environment": "production",
                "project": "core-infra"
            }
        }
        """
        provider = self.providers[CloudProvider(config['provider'])]
        instances = []
        
        # 1. 创建网络
        network_config = await self._create_network(
            provider, config
        )
        
        # 2. 创建多个实例
        for i in range(config['instance_count']):
            instance_config = {
                'ImageId': self._get_ami_id(config['os']),
                'InstanceType': config['instance_type'],
                'SubnetId': network_config['subnet_id'],
                'KeyName': config['security']['key_pair_name'],
                'BlockDeviceMappings': [
                    {
                        'DeviceName': '/dev/xvda',
                        'Ebs': {'VolumeSize': config['storage']['root_volume_size']}
                    }
                ],
                'TagSpecifications': [{
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': k, 'Value': v} 
                        for k, v in config['tags'].items()
                    ]
                }]
            }
            
            instance = await provider.create_instance(instance_config)
            instances.append(instance)
            await asyncio.sleep(2)  # 避免API限流
        
        # 3. 配置安全组
        await self._configure_security(
            provider, instances, config['security']
        )
        
        # 4. 分配弹性IP
        for instance in instances:
            elastic_ip = await provider.allocate_elastic_ip(
                instance.instance_id
            )
            instance.public_ip = elastic_ip
        
        return instances
    
    async def delete_vps_cluster(self, cluster_id: str):
        """删除整个集群"""
        # 实现方式：通过tag检查所有资源，逐个删除
        pass
    
    async def _create_network(self, provider, config) -> Dict:
        """创建VPC和子网"""
        pass
    
    async def _configure_security(self, provider, instances, security_config):
        """配置防火墙和密钥"""
        pass
```

### 3. 脚本执行器 (SSH/Ansible)

```python
# executors/ssh_executor.py
import asyncio
import aioparamiko as paramiko
from pathlib import Path

class SSHExecutor:
    """远程脚本执行"""
    
    def __init__(self, private_key_path: str):
        self.private_key_path = Path(private_key_path)
        self.key = paramiko.RSAKey.from_private_key_file(str(self.private_key_path))
    
    async def execute_command(self, 
                             host: str, 
                             username: str,
                             command: str,
                             timeout: int = 300) -> Dict[str, Any]:
        """
        执行单个命令
        
        返回: {"stdout": "...", "stderr": "...", "exit_code": 0}
        """
        async with paramiko.SSHClient() as client:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            await asyncio.wait_for(
                client.connect(
                    host,
                    username=username,
                    pkey=self.key,
                    look_for_keys=False
                ),
                timeout=10
            )
            
            stdin, stdout, stderr = await client.exec_command(command)
            
            output = await asyncio.wait_for(
                stdout.read(),
                timeout=timeout
            )
            errors = await stderr.read()
            
            return {
                "stdout": output.decode('utf-8'),
                "stderr": errors.decode('utf-8'),
                "exit_code": stdout.channel.recv_exit_status()
            }
    
    async def upload_file(self, host: str, username: str,
                         local_path: str, remote_path: str) -> bool:
        """上传文件"""
        async with paramiko.SSHClient() as client:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            await client.connect(host, username=username, pkey=self.key)
            
            async with client.open_sftp() as sftp:
                await sftp.put(local_path, remote_path)
        return True
    
    async def run_script(self, host: str, username: str,
                        script_path: str) -> Dict[str, Any]:
        """运行本地脚本"""
        with open(script_path, 'r') as f:
            script_content = f.read()
        
        # 将脚本上传到远程
        remote_script = f"/tmp/script_{int(time.time())}.sh"
        await self.upload_file(host, username, script_path, remote_script)
        
        # 执行脚本
        result = await self.execute_command(
            host, username,
            f"bash {remote_script}"
        )
        
        # 清理
        await self.execute_command(host, username, f"rm {remote_script}")
        
        return result
```

### 4. K3S集群搭建

```python
# orchestration/k3s_manager.py
import yaml
from typing import List

class K3SManager:
    """K3S Kubernetes集群管理"""
    
    def __init__(self, ssh_executor: SSHExecutor):
        self.ssh_executor = ssh_executor
    
    async def setup_k3s_cluster(self,
                               master_nodes: List[Instance],
                               worker_nodes: List[Instance],
                               config: Dict[str, Any]) -> Dict[str, Any]:
        """
        搭建K3S集群
        
        config例子:
        {
            "k3s_version": "v1.27.0",
            "network_plugin": "flannel",  # 或 "calico"
            "service_cidr": "10.43.0.0/16",
            "cluster_cidr": "10.42.0.0/16",
            "ingress_class": "traefik"
        }
        """
        
        # 第1步: 系统准备
        await self._prepare_nodes(master_nodes + worker_nodes)
        
        # 第2步: 初始化主节点
        master_ip = master_nodes[0].private_ip
        token = await self._init_master_node(
            master_nodes[0], config
        )
        
        # 第3步: 加入工作节点
        for worker in worker_nodes:
            await self._join_worker_node(worker, master_ip, token)
        
        # 第4步: 部署CNI和其他组件
        kubeconfig = await self._get_kubeconfig(master_nodes[0])
        await self._deploy_cni(master_nodes[0], config)
        
        return {
            "cluster_name": config.get("cluster_name", "k3s-cluster"),
            "master_nodes": [m.instance_id for m in master_nodes],
            "worker_nodes": [w.instance_id for w in worker_nodes],
            "master_ip": master_ip,
            "token": token,
            "kubeconfig": kubeconfig
        }
    
    async def _prepare_nodes(self, nodes: List[Instance]):
        """系统初始化"""
        prepare_script = """
#!/bin/bash
set -e

# 更新系统
apt-get update && apt-get upgrade -y

# 安装必要工具
apt-get install -y curl wget git vim htop

# 关闭swap
swapoff -a
sed -i '/ swap / s/^/#/' /etc/fstab

# 配置内核参数
cat > /etc/sysctl.d/99-k3s.conf << 'EOF'
net.ipv4.ip_forward=1
net.bridge.bridge-nf-call-iptables=1
net.bridge.bridge-nf-call-ip6tables=1
fs.file-max=655360
fs.inotify.max_user_watches=524288
EOF

sysctl --system

# 加载必要模块
modprobe overlay
modprobe br_netfilter

echo "Node preparation completed!"
"""
        
        for node in nodes:
            print(f"准备节点: {node.instance_id}")
            result = await self.ssh_executor.execute_command(
                node.public_ip, "ubuntu",
                prepare_script,
                timeout=600
            )
            
            if result['exit_code'] != 0:
                raise Exception(f"节点准备失败: {result['stderr']}")
    
    async def _init_master_node(self, master: Instance, 
                               config: Dict) -> str:
        """初始化主节点"""
        
        install_script = f"""
#!/bin/bash
set -e

export K3S_TOKEN=$(head -c 32 /dev/urandom | base64)
export K3S_KUBECONFIG_MODE="644"

curl -sfL https://get.k3s.io | \
  INSTALL_K3S_VERSION="{config.get('k3s_version', 'v1.27.0')}" \
  K3S_CLUSTER_INIT=true \
  K3S_TOKEN="${{K3S_TOKEN}}" \
  sh -s - \
  --cluster-cidr={config.get('cluster_cidr', '10.42.0.0/16')} \
  --service-cidr={config.get('service_cidr', '10.43.0.0/16')} \
  --flannel-backend={config.get('network_plugin', 'flannel')}

echo "${{K3S_TOKEN}}"
"""
        
        result = await self.ssh_executor.execute_command(
            master.public_ip, "ubuntu", install_script, timeout=600
        )
        
        if result['exit_code'] != 0:
            raise Exception(f"Master初始化失败: {result['stderr']}")
        
        token = result['stdout'].strip().split('\n')[-1]
        return token
    
    async def _join_worker_node(self, worker: Instance,
                               master_ip: str, token: str):
        """加入工作节点"""
        
        join_script = f"""
#!/bin/bash
set -e

curl -sfL https://get.k3s.io | K3S_URL="https://{master_ip}:6443" \
  K3S_TOKEN="{token}" sh -

echo "Worker node joined!"
"""
        
        result = await self.ssh_executor.execute_command(
            worker.public_ip, "ubuntu", join_script, timeout=600
        )
        
        if result['exit_code'] != 0:
            raise Exception(f"Worker加入失败: {result['stderr']}")
    
    async def _get_kubeconfig(self, master: Instance) -> str:
        """获取kubeconfig"""
        result = await self.ssh_executor.execute_command(
            master.public_ip, "ubuntu",
            "sudo cat /etc/rancher/k3s/k3s.yaml"
        )
        
        if result['exit_code'] != 0:
            raise Exception("获取kubeconfig失败")
        
        kubeconfig = result['stdout']
        # 替换localhost为实际IP
        kubeconfig = kubeconfig.replace(
            'https://127.0.0.1:6443',
            f'https://{master.public_ip}:6443'
        )
        
        return kubeconfig
    
    async def _deploy_cni(self, master: Instance, config: Dict):
        """部署网络插件"""
        pass
```

### 5. Agent核心引擎 (FastAPI + Claude API)

```python
# agent/ops_agent.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json

class TaskRequest(BaseModel):
    user_query: str  # 自然语言请求
    context: Dict[str, Any] = {}  # 额外上下文

class OpsAgent:
    """运维自动化Agent"""
    
    def __init__(self):
        self.app = FastAPI()
        self.vps_manager = None
        self.ssh_executor = None
        self.k3s_manager = None
        self._setup_routes()
    
    def _setup_routes(self):
        @self.app.post("/task")
        async def execute_task(request: TaskRequest):
            """处理用户任务请求"""
            
            # 1. 使用Claude理解任务
            task_plan = await self._understand_task(request.user_query)
            
            # 2. 验证权限
            await self._verify_permissions(task_plan)
            
            # 3. 执行任务
            result = await self._execute_plan(task_plan)
            
            # 4. 记录审计日志
            await self._log_audit(request.user_query, task_plan, result)
            
            return result
    
    async def _understand_task(self, query: str) -> Dict[str, Any]:
        """使用Claude理解自然语言查询"""
        
        # 构造系统提示
        system_prompt = """
你是一个云基础设施运维专家Agent。

用户会给你自然语言的运维任务，你需要解析成结构化的执行计划。

支持的操作：
1. VPS操作: create_vps, delete_vps, reboot_vps, configure_security_group
2. 存储操作: create_volume, attach_volume, delete_volume
3. 网络操作: create_vpc, create_subnet, allocate_elastic_ip
4. K3S操作: setup_k3s_cluster, deploy_app, upgrade_cluster
5. 脚本执行: run_script, execute_command, upload_file

你必须返回JSON格式的执行计划，包含：
{
    "operation": "操作类型",
    "parameters": {...},
    "validation_rules": [...],
    "estimated_time": "预计耗时",
    "risk_level": "低/中/高"
}
"""
        
        # 调用Claude API
        import anthropic
        client = anthropic.Anthropic()
        
        message = client.messages.create(
            model="claude-opus-4-1",
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {"role": "user", "content": query}
            ]
        )
        
        # 解析响应
        response_text = message.content[0].text
        task_plan = json.loads(response_text)
        
        return task_plan
    
    async def _execute_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务计划"""
        
        operation = plan['operation']
        params = plan['parameters']
        
        try:
            if operation == 'create_vps':
                result = await self.vps_manager.create_vps_cluster(params)
            
            elif operation == 'setup_k3s_cluster':
                result = await self.k3s_manager.setup_k3s_cluster(
                    params['master_nodes'],
                    params['worker_nodes'],
                    params['config']
                )
            
            elif operation == 'run_script':
                result = await self.ssh_executor.run_script(
                    params['host'],
                    params['username'],
                    params['script_path']
                )
            
            else:
                raise ValueError(f"未知操作: {operation}")
            
            return {
                "status": "success",
                "operation": operation,
                "result": result
            }
        
        except Exception as e:
            return {
                "status": "failed",
                "operation": operation,
                "error": str(e)
            }
    
    async def _verify_permissions(self, plan: Dict):
        """验证用户权限"""
        # 实现权限检查逻辑
        pass
    
    async def _log_audit(self, query: str, plan: Dict, result: Dict):
        """记录审计日志"""
        # 实现审计日志记录
        pass
```

## 部署指南

### 环境要求

```
Python 3.10+
Docker & Docker Compose
SSH密钥对（用于VPS访问）
云平台API凭证（AWS、阿里云、腾讯云）
```

### 快速启动

```bash
# 1. 克隆项目
git clone <repo-url>
cd ops-agent
python -m venv venv
source venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置凭证
cp .env.example .env
# 编辑.env文件，添加云平台凭证和SSH密钥

# 4. 启动Agent
docker-compose up -d

# 5. 访问API
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "在AWS 北京区域创建一个3节点的K3S集群，实例类型为t3.medium"
  }'
```

## 任务示例

### 示例1: 创建K3S集群

```json
{
  "user_query": "在阿里云上创建一个生产级别的K3S集群，3个master节点和5个worker节点，使用ubuntu 22.04，每个节点100GB存储"
}
```

### 示例2: 执行运维脚本

```json
{
  "user_query": "在所有k3s-cluster标签的实例上执行系统更新并检查磁盘空间"
}
```

### 示例3: 安全组配置

```json
{
  "user_query": "为production环境的所有VPS配置防火墙：开放22（SSH）、80（HTTP）、443（HTTPS）、6443（Kubernetes API）端口"
}
```

## 安全最佳实践

1. **凭证管理**
- 使用HashiCorp Vault存储敏感信息
- 定期轮换API密钥和SSH密钥
- 实现MFA认证
1. **权限控制**
- 基于角色的访问控制(RBAC)
- 任务审批工作流（高危操作需批准）
- 操作限流和速率限制
1. **审计日志**
- 记录所有操作（WHO, WHAT, WHEN, WHERE, WHY）
- 长期存储（至少6个月）
- 定期审查异常操作
1. **故障恢复**
- 实现幂等性（重复执行结果相同）
- 自动回滚机制
- 备份和恢复计划

## 后续扩展方向

1. **监控集成**
- Prometheus指标收集
- 告警和自动修复
- 成本优化建议
1. **多云成本管理**
- 成本预测和优化
- 资源标签强制
- 定期成本报告
1. **CI/CD集成**
- GitOps工作流
- 自动化部署管道
- 蓝绿部署支持
1. **高级功能**
- 灾难恢复自动化
- 跨云迁移工具
- 性能基准测试
