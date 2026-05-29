# Phase 2: IaC 执行引擎 — 实现计划

> **For Hermes:** Use executing-plans skill to implement this plan task-by-task.

**Goal:** 将 Terraform 集成到 Streamlit 驾驶舱，实现「plan → 冲突检查 → apply」完整链路

**Architecture:** 新增 `app/utils/terraform_executor.py` 作为 Terraform 执行抽象层，含 plan/apply/destroy 三个操作 + 实时输出流。UI 层新增「Terraform 模式」开关，切换模拟/真实 IaC。

**Tech Stack:** Python subprocess, Terraform CLI, Streamlit session_state

---

## 前置条件

- [x] Terraform 模块 `infrastructure/modules/vpc/` 已就绪
- [x] CIDR 冲突引擎 `app/utils/network.py` 已就绪
- [ ] 需要安装 Terraform CLI（检查或安装）

---

### Task 1: 安装 Terraform CLI

**Objective:** 确保系统有 terraform 可执行文件

**Files:**
- 无新建文件

**Step 1: 检查是否已安装**

```bash
which terraform && terraform version
```

**Step 2: 如未安装，安装 Terraform**

```bash
wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | tee /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/hashicorp.list
apt-get update && apt-get install -y terraform
```

**Step 3: 验证**

```bash
terraform version
```

预期输出: `Terraform v1.x.x`

---

### Task 2: 创建 Terraform 执行器模块

**Objective:** 封装 terraform plan/apply/destroy 的 subprocess 调用

**Files:**
- Create: `app/utils/terraform_executor.py`

**代码:**

```python
"""Terraform 执行引擎 — plan/apply/destroy 的 Python 封装"""

import subprocess
import os
import json
import tempfile
from dataclasses import dataclass
from typing import Optional


@dataclass
class TerraformResult:
    success: bool
    output: str
    plan_summary: str = ""
    vpc_id: str = ""
    error: str = ""


class TerraformExecutor:
    """封装 Terraform CLI，管理工作目录和状态文件"""

    def __init__(self, module_path: str, workspace_dir: Optional[str] = None):
        """
        Args:
            module_path: Terraform 模块路径（如 infrastructure/modules/vpc）
            workspace_dir: 工作目录（存放 tfvars 和 state），默认自动创建临时目录
        """
        self.module_path = os.path.abspath(module_path)
        self.workspace_dir = workspace_dir or tempfile.mkdtemp(prefix="tf-workspace-")

    def _run(self, args: list[str], capture: bool = True) -> TerraformResult:
        """执行 terraform 命令"""
        cmd = ["terraform"] + args
        try:
            result = subprocess.run(
                cmd,
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=300,
            )
            output = result.stdout + result.stderr
            return TerraformResult(
                success=(result.returncode == 0),
                output=output,
            )
        except subprocess.TimeoutExpired:
            return TerraformResult(success=False, output="", error="terraform 命令超时 (300s)")
        except FileNotFoundError:
            return TerraformResult(success=False, output="", error="未找到 terraform 命令，请安装 Terraform CLI")

    def init(self) -> TerraformResult:
        """terraform init — 初始化工作目录"""
        # 将 module 路径作为 source 写入工作目录
        main_tf = os.path.join(self.workspace_dir, "main.tf")
        with open(main_tf, "w") as f:
            f.write(f'module "vpc" {{\n  source = "{self.module_path}"\n}}\n')
        return self._run(["init"])

    def plan(self, vars_dict: dict) -> TerraformResult:
        """terraform plan — 预览变更"""
        tfvars_path = self._write_tfvars(vars_dict)
        return self._run(["plan", f"-var-file={tfvars_path}", "-no-color"])

    def apply(self, vars_dict: dict) -> TerraformResult:
        """terraform apply — 执行变更"""
        tfvars_path = self._write_tfvars(vars_dict)
        result = self._run(["apply", "-auto-approve", f"-var-file={tfvars_path}", "-no-color"])
        if result.success:
            vpc_id = self._extract_output("vpc_id")
            result.vpc_id = vpc_id or ""
        return result

    def destroy(self) -> TerraformResult:
        """terraform destroy — 销毁资源"""
        return self._run(["destroy", "-auto-approve", "-no-color"])

    def _write_tfvars(self, vars_dict: dict) -> str:
        """动态生成 terraform.tfvars 文件"""
        path = os.path.join(self.workspace_dir, "terraform.tfvars")
        with open(path, "w") as f:
            for key, value in vars_dict.items():
                if isinstance(value, str):
                    f.write(f'{key} = "{value}"\n')
                elif isinstance(value, bool):
                    f.write(f"{key} = {str(value).lower()}\n")
                elif isinstance(value, dict):
                    f.write(f"{key} = {json.dumps(value)}\n")
        return path

    def _extract_output(self, key: str) -> Optional[str]:
        """提取 terraform output 值"""
        result = self._run(["output", "-raw", key])
        if result.success:
            return result.output.strip()
        return None
```

---

### Task 3: 在 Streamlit 驾驶舱接入 Terraform 引擎

**Objective:** 在 app.py 中集成 Terraform 模式，支持 plan + apply + CIDR 检查

**Files:**
- Modify: `app/app.py` — 添加 Terraform 模式区域

**改动点:**

在 sidebar 的「创建新 VPC」表单前，增加部署模式选择：

```python
# 部署引擎选择
deploy_mode = st.sidebar.radio(
    "⚙️ 部署引擎",
    ["🧪 模拟模式", "🏗️ Terraform 模式"],
    horizontal=True,
)
use_terraform = (deploy_mode == "🏗️ Terraform 模式")
```

修改表单提交逻辑：

```python
if submitted:
    if not cidr:
        st.sidebar.error("CIDR 不能为空")
    else:
        if use_terraform:
            _handle_terraform_deploy(cidr, vpc_name, region)
        else:
            _handle_mock_deploy(cidr, vpc_name, region)
```

新增 Terraform 部署处理函数：

```python
def _handle_terraform_deploy(cidr: str, vpc_name: str, region: str):
    """Terraform 模式：plan → CIDR检查 → apply"""
    from app.utils.network import validate_network_plan
    from app.utils.terraform_executor import TerraformExecutor

    # 1. CIDR 冲突检查
    existing_cidrs = [v["CIDR"] for v in st.session_state.vpcs.get(region, [])]
    valid, msg = validate_network_plan(cidr, existing_cidrs)
    if not valid:
        st.sidebar.error(f"❌ {msg}")
        return

    # 2. Terraform init
    with st.spinner("🔧 初始化 Terraform..."):
        tf = TerraformExecutor("infrastructure/modules/vpc")
        result = tf.init()
        if not result.success:
            st.sidebar.error(f"Terraform init 失败:\n```\n{result.output[-500:]}\n```")
            return

    # 3. Terraform plan
    with st.spinner("📋 生成执行计划..."):
        plan_result = tf.plan({
            "cidr_block": cidr,
            "vpc_name": vpc_name or f"ops-agent-{uuid.uuid4().hex[:8]}",
            "tags": json.dumps({"Environment": "ops-agent", "Region": region}),
        })
        if not plan_result.success:
            st.sidebar.error(f"Plan 失败:\n```\n{plan_result.output[-1000:]}\n```")
            return

    # 4. Terraform apply
    with st.spinner("🚀 执行部署..."):
        apply_result = tf.apply({
            "cidr_block": cidr,
            "vpc_name": vpc_name or f"ops-agent-{uuid.uuid4().hex[:8]}",
            "tags": json.dumps({"Environment": "ops-agent", "Region": region}),
        })

    if apply_result.success:
        new_vpc = {
            "VPC ID": apply_result.vpc_id or "pending",
            "CIDR": cidr,
            "State": "available",
            "IsDefault": False,
            "Name": vpc_name or "ops-agent",
        }
        st.session_state.vpcs[region].append(new_vpc)
        timestamp = time.strftime("%H:%M:%S")
        st.session_state.deploy_log.insert(0, {
            "time": timestamp,
            "region": region,
            "vpc_id": new_vpc["VPC ID"],
            "cidr": cidr,
            "status": "✅ Terraform 部署成功",
        })
        st.sidebar.success(f"✅ VPC 创建成功！\n\n`{new_vpc['VPC ID']}` → {cidr}")
        # 显示 plan 输出
        with st.expander("📋 Terraform Plan 详情"):
            st.code(plan_result.output[-2000:])
        st.balloons()
    else:
        st.sidebar.error(f"Terraform apply 失败:\n```\n{apply_result.output[-1000:]}\n```")
```

同时将原有模拟逻辑抽取为 `_handle_mock_deploy(cidr, vpc_name, region)` 函数。

---

### Task 4: 添加 terraform plan 输出实时展示

**Objective:** 在 UI 中展示 terraform plan 详情 + apply 日志

**Files:**
- Modify: `app/app.py`

**改动点:**

在 Terraform deploy 函数中，plan 完成后使用 `st.expander` 折叠展示 plan 输出。apply 完成后展示 apply 日志。已经在 Task 3 的代码中包含。

---

### Task 5: 提交并推送

**Objective:** 将所有变更提交到 Git

**Files:**
- `git add` 所有变更

```bash
git add app/app.py app/utils/terraform_executor.py
git commit -m "feat: Phase 2 — Terraform IaC 执行引擎集成

- 新增 terraform_executor.py: plan/apply/destroy 封装
- Streamlit 驾驶舱接入 Terraform 模式 (plan → CIDR检查 → apply)
- 保留模拟模式，通过 radio 切换
- terraform plan 输出实时展示"
git push origin main
```
