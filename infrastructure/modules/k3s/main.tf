# K3s 模块 — 单节点 Kubernetes 部署
# 用法: module "k3s_cluster" { source = "./modules/k3s" ... }

variable "instance_type" {
  description = "EC2 实例类型"
  type        = string
  default     = "t3.medium"
}

variable "vpc_id" {
  description = "目标 VPC ID"
  type        = string
}

variable "subnet_id" {
  description = "目标子网 ID"
  type        = string
}

variable "key_name" {
  description = "SSH 密钥对名称"
  type        = string
  default     = null
}

variable "cluster_name" {
  description = "K3s 集群名称"
  type        = string
  default     = "ops-agent-cluster"
}

resource "aws_instance" "k3s_node" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  subnet_id     = var.subnet_id
  key_name      = var.key_name
  user_data     = file("${path.module}/user_data.sh")

  tags = {
    Name      = var.cluster_name
    ManagedBy = "ops-agent"
  }
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

output "instance_id" {
  value = aws_instance.k3s_node.id
}

output "public_ip" {
  value = aws_instance.k3s_node.public_ip
}
