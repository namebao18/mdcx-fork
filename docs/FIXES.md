# MDCX 修复说明

## 问题 1: CA 证书缺失

### 现象
```
curl: (77) error setting certificate file: /etc/ssl/certs/ca-certificates.crt
Exception: 网络请求错误: GET https://xxx 失败: HTTP 403
```

### 原因
基础镜像 `stainless403/mdcx-builtin-gui-base` 未安装 `ca-certificates` 包，导致 HTTPS 请求无法验证证书。

### 修复
在 Dockerfile 中添加：
```dockerfile
USER root
RUN apt-get update && apt-get install -y ca-certificates && update-ca-certificates
USER app
```

---

## 问题 2: 异常未捕获导致任务崩溃

### 现象
```
Exception: 网络请求错误: GET https://www.prestige-av.com/api/search?searchText=ABF-050 ... 失败: HTTP 403
⛔️ 刮削已手动停止！
```

### 原因
`mdcx/crawlers/prestige.py:91` 抛出未处理异常，导致整个刮削任务崩溃。

### 修复
在 `main()` 函数中添加 try/except 捕获异常，单个文件失败不影响全量任务。

```python
def main(keyword: str) -> dict:
    """主函数 - 修复版"""
    try:
        # 搜索和解析逻辑...
        return result
    except Exception as e:
        # 捕获所有异常，不再崩溃
        print(f"[prestige] 刮削失败 {keyword}: {e}")
        return {"error": str(e), "keyword": keyword}
```

**修复文件：** `mdcx/crawlers/prestige.py`

---

## 问题 3: 防重复刮削误判（计划中）

### 现象
已刮削成功的文件（如 `IPX-916`）被重新刮削时，MDCX 检测到目标目录已存在同名文件，将其移入失败目录。

### 计划
添加跳过逻辑：如果目标目录已存在同名 `.nfo` 文件且内容完整，直接跳过。

---

## 构建镜像

```bash
cd docker
docker compose build --no-cache
docker compose up -d
```

## 验证修复

```bash
# 验证 CA 证书
docker exec mdcx-fixed curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 https://httpbin.org/get
# 应返回 200

# 验证异常处理
# 在 Web UI 手动触发刮削，观察是否因单个文件失败而崩溃
```
