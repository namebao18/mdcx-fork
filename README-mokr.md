# MDCx 魔改版

本仓库是 [Hazard804/mdcx](https://github.com/Hazard804/mdcx) 的完整源码 fork，
在上游基础上修了两个问题，并提供一个可直接部署的镜像。

## 镜像

```
ghcr.io/namebao18/mdcx:mokr-v2
```

## 修了什么

### 1. HTTPS 证书缺失，导致刮削全部失败

上游报错（藏在 HTTP 403 后面）：

```
ErrCode: 77, Reason: 'error setting certificate verify locations:
CAfile: /tmp/_MEIn88rZY/curl_cffi/cacert.pem CApath: none'
```

上游用 PyInstaller 打包，运行时把资源解包到 `/tmp/_MEIxxxx/`，
`curl_cffi` 的 `cacert.pem` 在部分环境下没有被打进去，TLS 握手直接失败，
外层看到的现象就是所有网站都返回 403。

修法：
- 镜像内安装 `ca-certificates` 并执行 `update-ca-certificates`
- 改为**源码运行**（不再运行上游那个打包好的 `/app/MDCx`），
  `curl_cffi` 直接用虚拟环境里的证书文件，不再依赖 `/tmp/_MEIxxxx/` 临时目录
- 启动时执行 `mokr-selfcheck` 自检，证书缺失会自动从系统证书目录补一份

### 2. 单个影片失败会把整批刮削任务带崩

`mdcx/crawlers/prestige.py` 的字段解析完全没有容错，
接口返回结构一变（或返回错误页）就抛未捕获异常，整个刮削任务中断。

修法（见本仓库 `mdcx/crawlers/prestige.py`）：
- 所有字段解析改成 `.get()` + 兜底默认值
- 整个 `_run` 包一层异常兜底，统一转成 `CralwerException`
- 效果：单个网站失败只算这个网站失败，其它数据源和整批任务不受影响

## 部署

按自己环境改好 `docker-compose.yml` 里的卷路径，然后：

```bash
docker compose up -d
```

网页界面：`http://<NAS 的 IP>:5800`

## 自行构建

```bash
docker build -t ghcr.io/namebao18/mdcx:mokr-v2 .
```

海外网络可覆盖默认源：

```bash
docker build --build-arg UV_INDEX_URL=https://pypi.org/simple/ \
             --build-arg UV_PYTHON_INSTALL_MIRROR= \
             -t ghcr.io/namebao18/mdcx:mokr-v2 .
```

## 改其它爬虫

`mdcx/crawlers/` 下每个文件对应一个数据源。要改哪个就直接改源码
（按同样思路：字段容错 + 异常兜底），改完重新构建镜像即可。

## 跟上游同步

```bash
git remote add upstream https://github.com/Hazard804/mdcx.git
git fetch upstream && git merge upstream/master
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
