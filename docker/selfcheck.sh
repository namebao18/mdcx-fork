#!/bin/sh
# 魔改版自检：确认 curl_cffi / certifi 的 CA 证书文件存在
# 原版报错: ErrCode 77, CAfile: /tmp/_MEIxxxx/curl_cffi/cacert.pem 不存在
set -u

SP=/app/.venv/lib
found=0
for f in $(find "$SP" -maxdepth 4 -name cacert.pem 2>/dev/null); do
  echo "  ✅ 证书文件: $f ($(wc -c < "$f") 字节)"
  found=1
done

if [ "$found" = "0" ]; then
  echo "  ⚠️ 未在虚拟环境中找到 cacert.pem，将从系统证书目录复制一份"
  SRC=/etc/ssl/certs/ca-certificates.crt
  TGT="$SP/python3.13/site-packages/curl_cffi/cacert.pem"
  if [ -f "$SRC" ] && [ -d "$(dirname "$TGT")" ]; then
    cp "$SRC" "$TGT" && echo "  ✅ 已复制到 $TGT"
  else
    echo "  ❌ 复制失败，请检查系统证书"
  fi
fi

echo "  ✅ 系统证书: $([ -f /etc/ssl/certs/ca-certificates.crt ] && echo 存在 || echo 缺失)"
