#!/bin/bash
# K3s 轻量级 Kubernetes 安装脚本
# 用于 EC2 user-data 自动部署

set -e

# 安装 K3s (单节点)
curl -sfL https://get.k3s.io | sh -s - \
  --write-kubeconfig-mode 644 \
  --disable traefik \
  --node-name "$(hostname)"

# 等待就绪
until kubectl get nodes &>/dev/null; do
  echo "等待 K3s 就绪..."
  sleep 5
done

echo "K3s 安装完成"
kubectl get nodes
