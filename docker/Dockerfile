# MDCX 修复版 Dockerfile
# 基于 stainless403/mdcx-builtin-gui-base 修复 CA 证书和异常处理问题

ARG BASE_IMAGE=stainless403/mdcx-builtin-gui-base:latest
FROM ${BASE_IMAGE}

# 修复 1: 安装 CA 证书（解决 HTTPS 请求失败）
USER root
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
    ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*
USER app

# 保留原始入口脚本
COPY --chown=app:app entrypoint.sh /init.d/99-mdcx-fix
RUN chmod +x /init.d/99-mdcx-fix

# 元数据
LABEL maintainer="alice@example.com" \
      description="MDCX 修复版 - 基于 Hazard804/mdcx，修复 CA 证书和异常处理"
