# MDCx 魔改版 (mdcx-mokr)

基于上游 [Hazard804/mdcx](https://github.com/Hazard804/mdcx) 源码修改。
镜像底座沿用 `stainless403/mdcx-builtin-gui-base`（自带 noVNC 网页界面），
但**不再运行官方打包好的二进制**，改为直接运行修改后的源码 ——
否则源码里的改动不会生效。

## 镜像

```
ghcr.io/namebao18/mdcx:mokr-v1
```

## 修了什么

### 1. HTTPS 证书缺失，导致刮削全部失败

原版报错（藏在 HTTP 403 后面）：

```
ErrCode: 77, Reason: 'error setting certificate verify locations:
CAfile: /tmp/_MEIn88rZY/curl_cffi/cacert.pem CApath: none'
```

原因：官方用 PyInstaller 打包，运行时把资源解包到 `/tmp/_MEIxxxx/`，
`curl_cffi` 的证书文件在部分环境下没有被打进去，握手就直接失败。

修法：
- 镜像里装 `ca-certificates` 并 `update-ca-certificates`
- 改成源码运行后，`curl_cffi` 直接用虚拟环境里的证书文件，
  不再依赖 `/tmp/_MEIxxxx/` 这个临时解包目录
- 启动时跑一次 `mokr-selfcheck` 自检，证书缺失会自动从系统证书目录补一份

### 2. 单个影片失败会把整批刮削任务带崩

原版 `mdcx/crawlers/prestige.py` 字段解析完全没有容错，接口返回结构一旦变化
（或返回错误页）就抛未捕获异常，整个刮削任务中断。

修法（见 `patches/prestige.py`）：
- 所有字段解析改成 `.get()` + 兜底默认值
- 整个 `_run` 包一层异常兜底，统一转成 `CralwerException`
- 效果：单个网站失败只算这个网站失败，其它数据源和整批任务不受影响

## 部署

`docker-compose.yml` 里按自己的路径改好卷映射，然后：

```bash
docker compose up -d
```

网页界面：`http://<NAS 的 IP>:5800`

## 自行构建

```bash
docker build -t ghcr.io/namebao18/mdcx:mokr-v1 .
```

国内网络慢可换源：

```bash
docker build \
  --build-arg UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
  --build-arg UV_PYTHON_INSTALL_MIRROR=https://registry.npmmirror.com/-/binary/python-build-standalone \
  -t ghcr.io/namebao18/mdcx:mokr-v1 .
```

## 改别的爬虫

`mdcx/crawlers/` 下每个文件对应一个数据源。要修改哪个：

1. 从上游仓库找到对应文件，按同样思路（字段容错 + 异常兜底）改好
2. 放到 `patches/` 下，并在 `Dockerfile` 里加一行 `COPY`
3. 重新构建镜像

## 跟上游同步

```bash
docker build --build-arg MDCX_REF=<新的上游 tag> -t ghcr.io/namebao18/mdcx:mokr-v1 .
```

## 目录说明

| 路径 | 用途 |
|------|------|
| `/app` | 源码目录（`main.py` 所在处） |
| `/app/.venv` | Python 虚拟环境 |
| `/mdcx-config` | MDCx 配置目录 |
| `/vol2/1000/1024` | 媒体库（按需修改） |

## 许可

跟随上游，GPLv3。仅供学习与技术交流使用，请遵守当地法律法规。
