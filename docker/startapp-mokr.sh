#!/bin/sh
# 魔改版启动脚本：不再运行打包好的 /app/MDCx，而是从源码启动
set -u

if [ -n "${DEBUG_CONTAINER:-}" ]; then
  echo "=========================!!!!!!!!=============================="
  echo "            I'm sleeping. Make yourself at home!"
  echo "=========================!!!!!!!!=============================="
  while :; do sleep 10; done
fi

export LC_ALL=zh_CN.UTF-8
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

cd /app

echo "🔍 运行环境自检..."
/usr/local/bin/mokr-selfcheck || true

if [ ! -x /app/.venv/bin/python ]; then
  echo "/!\\ 虚拟环境缺失: /app/.venv/bin/python 不存在，容器无法启动。"
  exit 5
fi

echo "⏳ 启动 MDCx（魔改版 · 源码运行）..."
exec /app/.venv/bin/python main.py
