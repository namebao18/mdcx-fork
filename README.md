# MDCX 修复版

基于 [Hazard804/mdcx](https://github.com/Hazard804/mdcx) 的修复镜像，解决 CA 证书缺失和异常处理问题。

## 修复内容

1. **CA 证书缺失** - Dockerfile 安装 ca-certificates 包
2. **异常处理** - `mdcx/crawlers/prestige.py` 添加 try/except，单个文件失败不影响全量任务

## 快速开始

```bash
cd docker
docker compose up -d --build
```

## 验证

```bash
# 验证 CA 证书
docker exec mdcx-fixed curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 https://httpbin.org/get
# 200
```

## 原仓库

- https://github.com/Hazard804/mdcx
- https://github.com/sqzw-x/mdcx
- https://github.com/northsea4/mdcx-docker
