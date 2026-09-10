# =====================================================================
# MDCx 魔改版 (mdcx-mokr)
#
# 底座沿用：stainless403/mdcx-builtin-gui-base（自带 noVNC 网页界面 + supervisor）
# 关键改动：不再运行官方打包好的二进制 /app/MDCx，改为直接运行本仓库里
#           「修改过的源码」。只有这样，源码级的修改才会真正生效。
#
# 相比上游 Hazard804/mdcx，本仓库修了两处：
#
#   1) HTTPS 证书缺失（curl error 77 / CAfile /tmp/_MEIxxxx/curl_cffi/cacert.pem）
#      现象：刮削全部失败，外层看起来是 HTTP 403，其实是本地证书文件找不到。
#      原因：官方用 PyInstaller 打包，运行时把资源解包到 /tmp/_MEIxxxx/，
#            curl_cffi 的 cacert.pem 有时没被打进去。
#      修法：① 镜像内装 ca-certificates 并 update-ca-certificates
#            ② 改成源码运行，curl_cffi 直接用虚拟环境里的证书，
#               不再依赖 /tmp/_MEIxxxx/ 这个临时目录
#            ③ 启动时跑 mokr-selfcheck 自检，证书缺失自动补一份
#
#   2) 单个影片失败会把整批刮削任务带崩
#      原因：mdcx/crawlers/prestige.py 字段解析完全没有容错，
#            接口返回结构一变（或返回错误页）就抛未捕获异常，整个任务中断。
#      修法：① 所有字段解析改成 .get() + 兜底默认值
#            ② 整个 _run 包一层异常兜底，统一转成 CralwerException
#            ③ 效果：单站失败只算这个站失败，其它数据源与整批任务不受影响
#
# 构建：
#   docker build -t ghcr.io/namebao18/mdcx:mokr-v1 .
# 换源（默认已走国内镜像，海外可覆盖）：
#   docker build --build-arg UV_INDEX_URL=https://pypi.org/simple/ \
#                --build-arg UV_PYTHON_INSTALL_MIRROR= \
#                -t ghcr.io/namebao18/mdcx:mokr-v1 .
# =====================================================================
FROM stainless403/mdcx-builtin-gui-base:v2-d20250909

USER root
ENV DEBIAN_FRONTEND=noninteractive

# 可调参数：Python 包源、CPython 下载源、uv 安装源
ARG UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG UV_PYTHON_INSTALL_MIRROR=https://registry.npmmirror.com/-/binary/python-build-standalone
ARG UV_INSTALLER_BASE=https://astral.sh

# ---------- 1. 系统依赖 + CA 证书（修复点 1 的一半） ----------
RUN apt-get update -qq \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      tzdata \
      python3-pip \
      python3-venv \
      libgl1 \
      libglib2.0-0 \
      libegl1 \
      libfontconfig1 \
      libdbus-1-3 \
      libnss3 \
      libxkbcommon-x11-0 \
      libxcb-cursor0 \
      libxcb-icccm4 \
      libxcb-image0 \
      libxcb-keysyms1 \
      libxcb-randr0 \
      libxcb-render-util0 \
      libxcb-shape0 \
      libxcb-xinerama0 \
      libxcb-xfixes0 \
      libasound2t64 \
 && update-ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# ---------- 2. 安装 uv ----------
RUN pip3 install --break-system-packages -q -i "${UV_INDEX_URL}" uv \
 || (timeout 180 curl -LsSf "${UV_INSTALLER_BASE}/uv/install.sh" | sh)
ENV PATH="/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# ---------- 3. 放入本仓库的魔改源码 ----------
WORKDIR /app
COPY . /app/
RUN rm -rf /app/.git /app/.venv /app/dist /app/build

# ---------- 4. 安装依赖（生成 /app/.venv） ----------
ENV UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    UV_INDEX_URL=${UV_INDEX_URL} \
    UV_PYTHON_INSTALL_MIRROR=${UV_PYTHON_INSTALL_MIRROR} \
    PYTHONDONTWRITEBYTECODE=1
# 注意：不用 --locked。uv 新版会认为上游 lockfile 需要更新；直接同步即可。
ENV UV_PYTHON_DOWNLOADS=automatic
RUN uv sync --no-dev --python 3.13 \
 && /app/.venv/bin/python -c "import PyQt6, curl_cffi, av, cv2; print('依赖导入 OK')"

# ---------- 5. 启动脚本：源码运行，替掉官方二进制 ----------
COPY docker/startapp-mokr.sh /startapp.sh
COPY docker/selfcheck.sh /usr/local/bin/mokr-selfcheck
RUN chmod 755 /startapp.sh /usr/local/bin/mokr-selfcheck \
 && rm -f /app/MDCx \
 && chown -R 1000:1000 /app

EXPOSE 5800 5900
