# 部署指南

## 快速部署

\`\`\`bash
# 1. 克隆仓库
git clone https://github.com/namebao18/mdcx-fork.git
cd mdcx-fork

# 2. 复制现有配置（可选）
cp /path/to/your/config.v2.json data/config/

# 3. 构建并启动
docker compose up -d --build
\`\`\`

## 配置说明

- 配置目录：`./data/config/`（映射到容器 `/mdcx-config`）
- 媒体库：`/vol2/1000/1024`（按实际路径调整）
- Web UI：http://localhost:5800

## 验证修复

\`\`\`bash
# 验证 CA 证书
docker exec mdcx-fixed curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 https://httpbin.org/get
# 应返回 200
\`\`\`

## 故障排查

### 容器无法启动
\`\`\`bash
docker logs mdcx-fixed
\`\`\`

### CA 证书修复失败
进入容器手动修复：
\`\`\`bash
docker exec -it mdcx-fixed bash
apt-get update && apt-get install -y ca-certificates
\`\`\`

### 配置丢失
配置备份在仓库的 `data/config/config.v2.json`，可手动恢复。
