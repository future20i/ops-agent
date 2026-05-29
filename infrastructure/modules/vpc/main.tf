# VPC 模块
# 用法: module "my_vpc" { source = "./modules/vpc" ... }

variable "cidr_block" {
  description = "VPC CIDR 地址块"
  type        = string
}

variable "vpc_name" {
  description = "VPC 名称标签"
  type        = string
  default     = "ops-agent-vpc"
}

variable "enable_dns_support" {
  description = "启用 DNS 支持"
  type        = bool
  default     = true
}

variable "enable_dns_hostnames" {
  description = "启用 DNS 主机名"
  type        = bool
  default     = true
}

variable "tags" {
  description = "额外标签"
  type        = map(string)
  default     = {}
}

resource "aws_vpc" "main" {
  cidr_block           = var.cidr_block
  enable_dns_support   = var.enable_dns_support
  enable_dns_hostnames = var.enable_dns_hostnames

  tags = merge(
    {
      Name = var.vpc_name
      ManagedBy = "ops-agent"
    },
    var.tags
  )
}

output "vpc_id" {
  value = aws_vpc.main.id
}

output "vpc_cidr" {
  value = aws_vpc.main.cidr_block
}
