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
  type    = bool
  default = true
}

variable "enable_dns_hostnames" {
  type    = bool
  default = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
