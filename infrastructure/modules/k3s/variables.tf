variable "instance_type" { type = string; default = "t3.medium" }
variable "vpc_id"          { type = string }
variable "subnet_id"       { type = string }
variable "key_name"        { type = string; default = null }
variable "cluster_name"    { type = string; default = "ops-agent-cluster" }
