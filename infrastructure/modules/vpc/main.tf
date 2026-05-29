# VPC 模块
# 用法: module "my_vpc" { source = "./modules/vpc" ... }

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
