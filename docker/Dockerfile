# MDCX 修复版 Dockerfile
# 基于 stainless403/mdcx-builtin-gui-base 修复 CA 证书和异常处理

ARG BASE_IMAGE=stainless403/mdcx-builtin-gui-base:latest
FROM ${BASE_IMAGE}

# 修复 1: 安装 CA 证书（解决 HTTPS 请求失败）
USER root
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
    ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*
USER app

# 修复 2: 复制修复后的 prestige.py（在容器启动时替换）
# 注意：PyInstaller 打包的二进制无法直接替换 pyc，需要完整源码
# 此处仅作标记，实际修复需要在源码级别修改

# 元数据
LABEL maintainer="alice@example.com" \
      description="MDCX 修复版 - 基于 Hazard804/mdcx，修复 CA 证书和异常处理"
