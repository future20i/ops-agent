"""AWS 客户端包装 — 安全凭证注入与客户端单例"""

import os
import boto3
from functools import lru_cache


@lru_cache(maxsize=32)
def get_ec2_client(region: str = "us-east-1") -> boto3.client:
    """
    获取 EC2 客户端（带缓存）。
    凭证优先级: 环境变量 > ~/.aws/credentials > IAM Role
    """
    return boto3.client(
        "ec2",
        region_name=region,
        # 不从代码硬编码凭证，依赖 AWS SDK 默认凭证链
    )


def list_vpcs(region: str) -> list[dict]:
    """获取指定地区的 VPC 列表"""
    client = get_ec2_client(region)
    response = client.describe_vpcs()
    return [
        {
            "VPC ID": v["VpcId"],
            "CIDR": v["CidrBlock"],
            "State": v["State"],
            "IsDefault": v["IsDefault"],
        }
        for v in response["Vpcs"]
    ]


def list_instances(region: str) -> list[dict]:
    """获取指定地区的 EC2 实例列表"""
    client = get_ec2_client(region)
    response = client.describe_instances()
    instances = []
    for res in response["Reservations"]:
        for inst in res["Instances"]:
            name = ""
            for tag in inst.get("Tags", []):
                if tag["Key"] == "Name":
                    name = tag["Value"]
            instances.append({
                "Instance ID": inst["InstanceId"],
                "Name": name,
                "Type": inst["InstanceType"],
                "State": inst["State"]["Name"],
                "AZ": inst["Placement"]["AvailabilityZone"],
            })
    return instances
