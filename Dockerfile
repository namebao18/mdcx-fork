# =====================================================================
# MDCx 魔改版 (mdcx-mokr)
#
# 底座不变：stainless403/mdcx-builtin-gui-base（自带 noVNC 网页界面 + supervisor）
# 关键改动：不再运行官方打包好的二进制 /app/MDCx，改为直接运行「修改后的源码」。
#           只有这样，源码里的修改才真正生效。
#
# 修复内容：
#   1. HTTPS 证书缺失（curl error 77 / CAfile /tmp/_MEIxxxx/curl_cffi/cacert.pem）
#      - 安装 ca-certificates 并 update-ca-certificates
#      - 源码运行时 curl_cffi 使用虚拟环境里的证书，不再依赖 PyInstaller
#        解包目录 /tmp/_MEIxxxx/ —— 原版正是在这里翻车
#      - 启动时执行 mokr-selfcheck 自检，证书缺失自动补
#   2. prestige.py 无异常兜底，单个影片失败会把整批任务带崩
#      - 字段解析全部改用 .get() 容错 + 默认值
#      - 整个 _run 包异常兜底，统一转成 CralwerException
#      - 效果：单站失败只算这个站失败，不影响其它数据源与整批任务
#
# 构建示例：
#   docker build -t ghcr.io/namebao18/mdcx:mokr-v1 .
# 国内网络慢可换源：
#   docker build \
#     --build-arg UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
#     --build-arg UV_PYTHON_INSTALL_MIRROR=https://registry.npmmirror.com/-/binary/python-build-standalone \
#     -t ghcr.io/namebao18/mdcx:mokr-v1 .
# =====================================================================
FROM stainless403/mdcx-builtin-gui-base:v2-d20250909

USER root
ENV DEBIAN_FRONTEND=noninteractive

# 可调参数：上游版本、Python 包源、CPython 下载源、uv 安装方式
ARG MDCX_REPO=https://github.com/Hazard804/mdcx.git
ARG MDCX_REF=220260517
ARG UV_INDEX_URL=https://pypi.org/simple/
ARG UV_PYTHON_INSTALL_MIRROR=
ARG UV_INSTALLER_BASE=https://astral.sh

# ---------- 1. 系统依赖 + CA 证书 ----------
RUN apt-get update -qq \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      git \
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
RUN curl -LsSf "${UV_INSTALLER_BASE}/uv/install.sh" | sh \
 || pip3 install --break-system-packages -q -i "${UV_INDEX_URL}" uv
ENV PATH="/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# ---------- 3. 拉取上游源码（固定版本，可复现） ----------
RUN rm -rf /app && git clone --depth 1 --branch "${MDCX_REF}" "${MDCX_REPO}" /app \
 || (rm -rf /app && git clone "${MDCX_REPO}" /app && cd /app && git checkout "${MDCX_REF}")

WORKDIR /app

# ---------- 4. 覆盖魔改文件 ----------
COPY patches/prestige.py /app/mdcx/crawlers/prestige.py

# ---------- 5. 安装项目依赖（生成 /app/.venv） ----------
ENV UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    UV_INDEX_URL=${UV_INDEX_URL} \
    UV_PYTHON_INSTALL_MIRROR=${UV_PYTHON_INSTALL_MIRROR} \
    PYTHONDONTWRITEBYTECODE=1
RUN uv sync --locked --no-dev --python 3.13 \
 && /app/.venv/bin/python -c "import PyQt6, curl_cffi, av, cv2; print('依赖导入 OK')"

# ---------- 6. 启动脚本：从源码运行，替掉官方二进制 ----------
COPY docker/startapp-mokr.sh /startapp.sh
COPY docker/selfcheck.sh /usr/local/bin/mokr-selfcheck
RUN chmod +x /startapp.sh /usr/local/bin/mokr-selfcheck \
 && rm -f /app/MDCx \
 && rm -rf /app/.git \
 && chown -R 1000:1000 /app

EXPOSE 5800 5900
