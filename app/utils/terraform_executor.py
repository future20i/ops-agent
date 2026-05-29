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
            return TerraformResult(
                success=False, output="", error="terraform 命令超时 (300s)"
            )
        except FileNotFoundError:
            return TerraformResult(
                success=False, output="", error="未找到 terraform 命令，请安装 Terraform CLI"
            )

    def init(self) -> TerraformResult:
        """terraform init — 初始化工作目录"""
        main_tf = os.path.join(self.workspace_dir, "main.tf")
        with open(main_tf, "w") as f:
            f.write(f'''variable "cidr_block" {{
  type = string
}}

variable "vpc_name" {{
  type    = string
  default = "ops-agent-vpc"
}}

variable "enable_dns_support" {{
  type    = bool
  default = true
}}

variable "enable_dns_hostnames" {{
  type    = bool
  default = true
}}

variable "tags" {{
  type    = map(string)
  default = {{}}
}}

module "vpc" {{
  source = "{self.module_path}"

  cidr_block           = var.cidr_block
  vpc_name             = var.vpc_name
  enable_dns_support   = var.enable_dns_support
  enable_dns_hostnames = var.enable_dns_hostnames
  tags                 = var.tags
}}

output "vpc_id" {{
  value = module.vpc.vpc_id
}}

output "vpc_cidr" {{
  value = module.vpc.vpc_cidr
}}
''')
        return self._run(["init"])

    def plan(self, vars_dict: dict) -> TerraformResult:
        """terraform plan — 预览变更"""
        tfvars_path = self._write_tfvars(vars_dict)
        return self._run(["plan", f"-var-file={tfvars_path}", "-no-color"])

    def apply(self, vars_dict: dict) -> TerraformResult:
        """terraform apply — 执行变更"""
        tfvars_path = self._write_tfvars(vars_dict)
        result = self._run(
            ["apply", "-auto-approve", f"-var-file={tfvars_path}", "-no-color"]
        )
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
