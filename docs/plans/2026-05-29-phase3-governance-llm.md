# Phase 3: 智能治理与反馈 — 实现计划

> **For Hermes:** Use executing-plans skill to implement this plan task-by-task.

**Goal:** 在 Terraform 部署前注入策略检查层 + LLM 智能错误分析，实现「检测 → 拦截 → AI 解释 → 建议修复」闭环

**Architecture:** 新增 `app/agents/governance.py`（策略引擎）和 `app/agents/llm_advisor.py`（LLM 顾问），在 plan 和 apply 之间插入治理检查点。违反规则时自动调用 LLM 生成中文解释和修复建议。

**Tech Stack:** Python dataclasses, Streamlit session_state, LLM API (OpenAI-compatible)

---

### Task 1: 创建治理策略引擎

**Objective:** 构建规则检查引擎，覆盖 CIDR/VPC/EC2/S3/IAM 五类规则

**Files:**
- Create: `app/agents/governance.py`

**Step 1: 编写策略引擎代码**

```python
"""治理策略引擎 — 部署前规则检查"""

from dataclasses import dataclass, field
from typing import List

@dataclass
class GovernanceRule:
    name: str
    resource: str
    description: str
    severity: str  # "block" | "warn"

@dataclass
class GovernanceViolation:
    rule: GovernanceRule
    detail: str
    suggestion: str

@dataclass
class GovernanceReport:
    passed: bool
    violations: List[GovernanceViolation] = field(default_factory=list)

class GovernanceEngine:
    """部署前策略检查引擎"""

    RULES = [
        GovernanceRule(
            name="cidr-overlap",
            resource="VPC",
            description="CIDR 地址块不得与已有网段重叠",
            severity="block",
        ),
        GovernanceRule(
            name="ssh-port-22",
            resource="EC2",
            description="禁止开放 SSH 22 端口，强制使用 SSM Session Manager",
            severity="block",
        ),
        GovernanceRule(
            name="s3-encryption",
            resource="Storage",
            description="S3 存储桶必须启用服务端加密",
            severity="block",
        ),
        GovernanceRule(
            name="iam-least-privilege",
            resource="IAM",
            description="遵循最小权限原则，Agent Role 仅授予必要权限",
            severity="warn",
        ),
        GovernanceRule(
            name="vpc-dns-enabled",
            resource="VPC",
            description="VPC 应启用 DNS 支持和 DNS 主机名",
            severity="warn",
        ),
        GovernanceRule(
            name="tags-required",
            resource="Global",
            description="所有资源必须包含 Environment 和 ManagedBy 标签",
            severity="warn",
        ),
    ]

    def check_vpc_deploy(self, cidr: str, existing_cidrs: list, config: dict) -> GovernanceReport:
        """检查 VPC 部署是否符合治理规则"""
        violations = []

        # CIDR 冲突检查
        from app.utils.network import validate_network_plan
        valid, msg = validate_network_plan(cidr, existing_cidrs)
        if not valid:
            violations.append(GovernanceViolation(
                rule=self._find_rule("cidr-overlap"),
                detail=msg,
                suggestion=f"建议更换 CIDR，可用范围如 10.{hash(cidr) % 256}.0.0/16",
            ))

        # DNS 检查
        if not config.get("enable_dns_support", True):
            violations.append(GovernanceViolation(
                rule=self._find_rule("vpc-dns-enabled"),
                detail="VPC DNS 支持未启用",
                suggestion="设置 enable_dns_support = true",
            ))

        # 标签检查
        tags = config.get("tags", {})
        missing = []
        if "Environment" not in tags:
            missing.append("Environment")
        if "ManagedBy" not in tags:
            missing.append("ManagedBy")
        if missing:
            violations.append(GovernanceViolation(
                rule=self._find_rule("tags-required"),
                detail=f"缺少必要标签: {', '.join(missing)}",
                suggestion=f"添加 tags: {{'Environment': 'production', 'ManagedBy': 'ops-agent'}}",
            ))

        return GovernanceReport(
            passed=len([v for v in violations if v.rule.severity == "block"]) == 0,
            violations=violations,
        )

    def _find_rule(self, name: str) -> GovernanceRule:
        for r in self.RULES:
            if r.name == name:
                return r
        return GovernanceRule(name=name, resource="Unknown", description="", severity="warn")
```

---

### Task 2: 创建 LLM 顾问模块

**Objective:** LLM 分析治理违规 + Terraform 错误，生成中文解释

**Files:**
- Create: `app/agents/llm_advisor.py`

```python
"""LLM 智能顾问 — 错误分析与修复建议"""

import os
import json
import urllib.request
from typing import Optional

class LLMAdvisor:
    """调用 LLM 分析运维错误并给出修复建议"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

    def analyze_violation(self, rule_name: str, detail: str) -> str:
        """分析治理违规并给出解释"""
        if not self.api_key:
            return self._fallback_analysis(rule_name, detail)

        prompt = f"""你是一个云运维安全专家。以下部署违反了治理规则：

规则：{rule_name}
详情：{detail}

请用中文简洁解释（3-5句）：
1. 为什么这个规则重要
2. 不修复会有什么风险
3. 如何修复"""
        return self._call_llm(prompt)

    def analyze_terraform_error(self, error_output: str) -> str:
        """分析 Terraform 错误"""
        if not self.api_key:
            return self._fallback_tf_analysis(error_output)

        prompt = f"""分析以下 Terraform 错误并给出中文修复建议（3-5句）：

```
{error_output[-2000:]}
```

输出格式：
1. 错误原因
2. 修复步骤"""
        return self._call_llm(prompt)

    def _call_llm(self, prompt: str) -> str:
        """调用 OpenAI-compatible API"""
        try:
            data = json.dumps({
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300,
                "temperature": 0.3,
            }).encode()
            req = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=data,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
            return resp["choices"][0]["message"]["content"]
        except Exception as e:
            return f"LLM 调用失败: {e}"

    def _fallback_analysis(self, rule_name: str, detail: str) -> str:
        """无 API Key 时的内置建议"""
        suggestions = {
            "cidr-overlap": "CIDR 重叠会导致路由冲突，两个 VPC 无法正常通信。请选择一个不与现有网段重叠的新 CIDR。",
            "ssh-port-22": "开放 SSH 22 端口是最常见的安全漏洞。建议使用 AWS SSM Session Manager 替代，无需开放入站端口。",
            "s3-encryption": "未加密的 S3 存储桶可能导致数据泄露。启用 SSE-S3 或 KMS 加密以保护静态数据。",
            "iam-least-privilege": "过度授权的 IAM Role 违反最小权限原则。建议仅授予 ec2:RunInstances 等必要权限。",
            "vpc-dns-enabled": "禁用 DNS 会导致 EC2 无法解析域名。建议启用 enableDnsSupport 和 enableDnsHostnames。",
            "tags-required": "缺少标签会导致资源难以追踪和成本分配。请添加 Environment 和 ManagedBy 标签。",
        }
        return suggestions.get(rule_name, f"违反规则「{rule_name}」: {detail}")
```

---

### Task 3: 在驾驶舱集成治理检查点

**Objective:** 在 Terraform 部署流程中插入策略检查 + LLM 分析

**Files:**
- Modify: `app/app.py` — 在 `_handle_terraform_deploy()` 的 plan 和 apply 之间插入治理检查

改动：在 plan 成功后、apply 前，调用 GovernanceEngine 检查 + LLM 分析违规，展示结果并要求用户确认。

---

### Task 4: 更新 agents/__init__.py 导出

**Objective:** 保证模块导入路径正确

**Files:**
- Modify: `app/agents/__init__.py`

---

### Task 5: 提交推送

**Files:** 所有变更
