#!/bin/bash
set -e

# 修复 CA 证书（每次启动确保存在）
if [ ! -f /etc/ssl/certs/ca-certificates.crt ]; then
    echo "[mdcx-fix] CA 证书缺失，正在修复..."
    apt-get update -qq && apt-get install -y -qq ca-certificates > /dev/null 2>&1
    update-ca-certificates
    echo "[mdcx-fix] CA 证书修复完成"
fi

# 执行原始入口脚本
exec /init
