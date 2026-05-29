"""K3S 集群部署引擎 — 模拟完整部署流程"""

import time
import uuid
import random
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class K3SNode:
    node_id: str
    role: str  # "master" | "worker"
    private_ip: str
    public_ip: str
    status: str  # "pending" | "preparing" | "joining" | "ready" | "failed"


@dataclass
class DeployStep:
    name: str
    description: str
    status: str  # "pending" | "running" | "done" | "failed"
    output: str = ""
    duration: float = 0


@dataclass
class K3SCluster:
    cluster_id: str
    name: str
    region: str
    k3s_version: str
    nodes: List[K3SNode] = field(default_factory=list)
    steps: List[DeployStep] = field(default_factory=list)
    kubeconfig: str = ""
    master_ip: str = ""
    token: str = ""


class K3SDeployer:
    """K3S 集群一键部署（模拟模式）"""

    K3S_VERSION = "v1.28.2+k3s1"
    PREPARE_COMMANDS = [
        "apt-get update && apt-get upgrade -y",
        "swapoff -a && sed -i '/ swap / s/^/#/' /etc/fstab",
        "modprobe overlay && modprobe br_netfilter",
        "sysctl --system  # 内核参数优化",
    ]
    MASTER_INIT_COMMAND = (
        "curl -sfL https://get.k3s.io | "
        "INSTALL_K3S_VERSION={version} K3S_TOKEN={token} "
        "sh -s - --cluster-init"
    )
    WORKER_JOIN_COMMAND = (
        "curl -sfL https://get.k3s.io | "
        "K3S_URL=https://{master_ip}:6443 K3S_TOKEN={token} sh -"
    )

    def deploy(
        self,
        cluster_name: str,
        region: str,
        master_count: int = 1,
        worker_count: int = 2,
        instance_type: str = "t3.medium",
    ) -> K3SCluster:
        """执行完整 K3S 部署流程"""

        cluster_id = str(uuid.uuid4())[:12]
        cluster = K3SCluster(
            cluster_id=cluster_id,
            name=cluster_name or f"k3s-{cluster_id[:8]}",
            region=region,
            k3s_version=self.K3S_VERSION,
        )

        # Step 1: 环境准备
        cluster.steps.append(self._run_step(
            "🔧 系统环境准备",
            f"为 {master_count + worker_count} 个节点安装依赖、关闭 swap、配置内核参数",
        ))
        time.sleep(0.8)
        cluster.steps[-1].status = "done"
        cluster.steps[-1].output = "\n".join(
            f"  ✅ node-{i}: {cmd.split('&&')[0].strip()}..."
            for i, cmd in enumerate(self.PREPARE_COMMANDS)
        )

        # Step 2: 创建节点
        cluster.steps.append(self._run_step(
            "🖥️ 创建节点实例",
            f"在 {region} 创建 {master_count} 个 master + {worker_count} 个 worker（{instance_type}）",
        ))
        time.sleep(1.0)
        for i in range(master_count):
            node = K3SNode(
                node_id=f"i-{uuid.uuid4().hex[:8]}",
                role="master",
                private_ip=self._gen_ip("10.0"),
                public_ip=self._gen_ip("54"),
                status="ready",
            )
            cluster.nodes.append(node)
        for i in range(worker_count):
            node = K3SNode(
                node_id=f"i-{uuid.uuid4().hex[:8]}",
                role="worker",
                private_ip=self._gen_ip("10.0"),
                public_ip=self._gen_ip("54"),
                status="ready",
            )
            cluster.nodes.append(node)
        cluster.steps[-1].status = "done"
        cluster.steps[-1].output = "\n".join(
            f"  ✅ {n.node_id} ({n.role}) — {n.public_ip}"
            for n in cluster.nodes
        )

        # Step 3: 初始化主节点
        cluster.steps.append(self._run_step(
            "⭐ 初始化 Master 节点",
            f"在 {cluster.nodes[0].node_id} 上安装 K3S Server",
        ))
        cluster.token = uuid.uuid4().hex[:32]
        cluster.master_ip = cluster.nodes[0].public_ip
        time.sleep(1.5)
        cluster.steps[-1].status = "done"
        cluster.steps[-1].output = (
            f"  ✅ K3S {self.K3S_VERSION} 已安装\n"
            f"  ✅ API Server: https://{cluster.master_ip}:6443\n"
            f"  🔑 Token: {cluster.token[:16]}..."
        )

        # Step 4: 加入工作节点
        if worker_count > 0:
            cluster.steps.append(self._run_step(
                "🔗 加入 Worker 节点",
                f"将 {worker_count} 个 Worker 加入集群",
            ))
            time.sleep(0.6 * worker_count)
            cluster.steps[-1].status = "done"
            cluster.steps[-1].output = "\n".join(
                f"  ✅ {n.node_id} 已加入集群"
                for n in cluster.nodes if n.role == "worker"
            )

        # Step 5: 集群验证
        cluster.steps.append(self._run_step(
            "✅ 集群验证",
            "检查节点状态、CoreDNS、指标服务",
        ))
        time.sleep(0.8)
        cluster.steps[-1].status = "done"
        cluster.steps[-1].output = (
            f"  ✅ {len(cluster.nodes)} 个节点全部 Ready\n"
            "  ✅ CoreDNS 运行正常\n"
            "  ✅ metrics-server 已部署"
        )

        # 生成 kubeconfig
        cluster.kubeconfig = self._gen_kubeconfig(cluster)

        return cluster

    def _run_step(self, name: str, description: str) -> DeployStep:
        return DeployStep(name=name, description=description, status="running")

    @staticmethod
    def _gen_ip(prefix: str) -> str:
        return f"{prefix}.{random.randint(1, 254)}.{random.randint(1, 254)}"

    @staticmethod
    def _gen_kubeconfig(cluster: K3SCluster) -> str:
        return f"""apiVersion: v1
kind: Config
clusters:
- cluster:
    certificate-authority-data: LS0tLS...（已省略）
    server: https://{cluster.master_ip}:6443
  name: {cluster.name}
contexts:
- context:
    cluster: {cluster.name}
    user: admin
  name: {cluster.name}
current-context: {cluster.name}
users:
- name: admin
  user:
    token: {cluster.token}
"""
