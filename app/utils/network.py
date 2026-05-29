"""网络工具模块 — CIDR 冲突检测与 IP 校验"""

import ipaddress
from typing import Tuple, List


def validate_network_plan(new_cidr: str, existing_cidrs: List[str]) -> Tuple[bool, str]:
    """
    检查新 CIDR 是否与已有网段冲突。

    Args:
        new_cidr:  新规划的 CIDR，如 "10.50.0.0/16"
        existing_cidrs: 已有 CIDR 列表

    Returns:
        (is_valid, message)
    """
    try:
        new_net = ipaddress.ip_network(new_cidr)
    except ValueError as e:
        return False, f"CIDR 格式无效: {new_cidr} — {e}"

    for cidr in existing_cidrs:
        try:
            existing_net = ipaddress.ip_network(cidr)
            if new_net.overlaps(existing_net):
                return False, f"网段冲突: {new_cidr} 与 {cidr} 重叠"
        except ValueError:
            continue

    return True, "验证通过"


def is_valid_cidr(cidr: str) -> bool:
    """快速校验 CIDR 格式是否合法"""
    try:
        ipaddress.ip_network(cidr)
        return True
    except ValueError:
        return False
