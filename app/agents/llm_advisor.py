"""LLM 智能顾问 — 错误分析与修复建议"""

import os
import json
import urllib.request
from typing import Optional


class LLMAdvisor:
    """调用 LLM 分析运维错误并给出修复建议"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url or os.environ.get(
            "OPENAI_BASE_URL", "https://api.openai.com/v1"
        )

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
            data = json.dumps(
                {
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 300,
                    "temperature": 0.3,
                }
            ).encode()
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
        """无 API Key 时的内置建议（离线可用）"""
        suggestions = {
            "cidr-overlap": (
                "**CIDR 重叠**会导致路由冲突，两个 VPC 无法正常通信。\n\n"
                "🔧 修复：选择一个不与现有网段重叠的新 CIDR 地址块。"
            ),
            "ssh-port-22": (
                "**开放 SSH 22 端口**是最常见的安全漏洞，易被暴力破解攻击。\n\n"
                "🔧 修复：使用 AWS SSM Session Manager 替代 SSH，无需开放任何入站端口。"
            ),
            "s3-encryption": (
                "**未加密的 S3 存储桶**可能导致敏感数据泄露。\n\n"
                "🔧 修复：启用 SSE-S3 或 KMS 加密保护静态数据。"
            ),
            "iam-least-privilege": (
                "**过度授权的 IAM Role** 违反最小权限原则，扩大攻击面。\n\n"
                "🔧 修复：仅授予 ec2:RunInstances 等必要权限，定期审计 IAM Policy。"
            ),
            "vpc-dns-enabled": (
                "**禁用 DNS** 会导致 EC2 实例无法解析域名。\n\n"
                "🔧 修复：设置 enable_dns_support = true, enable_dns_hostnames = true。"
            ),
            "tags-required": (
                "**缺少必要标签**会导致资源难以追踪和成本分配。\n\n"
                "🔧 修复：添加 Environment 和 ManagedBy 标签，便于审计和成本分析。"
            ),
        }
        return suggestions.get(
            rule_name, f"违反规则「{rule_name}」: {detail}"
        )

    def _fallback_tf_analysis(self, error_output: str) -> str:
        """离线 Terraform 错误分析"""
        if "AccessDenied" in error_output or "Unauthorized" in error_output:
            return "**权限不足**：AWS 凭证缺少必要权限。请检查 IAM Policy 是否包含 ec2:CreateVpc 等权限。"
        if "InvalidVpcID.NotFound" in error_output:
            return "**VPC 不存在**：引用的 VPC ID 无效或已被删除。请确认 VPC ID 是否正确。"
        if "cidr" in error_output.lower() and "overlap" in error_output.lower():
            return "**CIDR 冲突**：新 CIDR 与已有网段重叠。请使用 ipaddress 模块检查后更换 CIDR。"
        return f"**Terraform 错误**：请检查以下输出中的具体错误信息：\n```\n{error_output[-500:]}\n```"
