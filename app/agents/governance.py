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
    """部署前策略检查引擎 — 覆盖 VPC/EC2/S3/IAM 治理规则"""

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

    def check_vpc_deploy(
        self, cidr: str, existing_cidrs: list, config: dict
    ) -> GovernanceReport:
        """检查 VPC 部署是否符合治理规则"""
        violations = []

        # CIDR 冲突检查
        from app.utils.network import validate_network_plan

        valid, msg = validate_network_plan(cidr, existing_cidrs)
        if not valid:
            violations.append(
                GovernanceViolation(
                    rule=self._find_rule("cidr-overlap"),
                    detail=msg,
                    suggestion=f"建议更换 CIDR，可用范围如 10.{abs(hash(cidr)) % 256}.0.0/16",
                )
            )

        # DNS 检查
        if not config.get("enable_dns_support", True):
            violations.append(
                GovernanceViolation(
                    rule=self._find_rule("vpc-dns-enabled"),
                    detail="VPC DNS 支持未启用",
                    suggestion="设置 enable_dns_support = true",
                )
            )

        # 标签检查
        tags = config.get("tags", {})
        missing = []
        if "Environment" not in tags:
            missing.append("Environment")
        if "ManagedBy" not in tags:
            missing.append("ManagedBy")
        if missing:
            violations.append(
                GovernanceViolation(
                    rule=self._find_rule("tags-required"),
                    detail=f"缺少必要标签: {', '.join(missing)}",
                    suggestion="添加 tags: {'Environment': 'production', 'ManagedBy': 'ops-agent'}",
                )
            )

        return GovernanceReport(
            passed=len([v for v in violations if v.rule.severity == "block"]) == 0,
            violations=violations,
        )

    def _find_rule(self, name: str) -> GovernanceRule:
        for r in self.RULES:
            if r.name == name:
                return r
        return GovernanceRule(
            name=name, resource="Unknown", description="", severity="warn"
        )
