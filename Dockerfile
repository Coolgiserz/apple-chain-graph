# 多阶段构建：node 打包前端 -> python 生成静态页 -> nginx 托管
# 镜像源可经 .env 覆盖为完整镜像名（推荐做法，官方源与镜像源都能正确解析）：
#   PYTHON_IMG=swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.11-slim
#   NODE_IMG=swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/node:20-slim
#   NGINX_IMG=swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/nginx:1.27-alpine
# 留空 / 不设 .env 时走官方源 python:3.11-slim / node:20-slim / nginx:1.27-alpine（docker.io 官方仓库）。
ARG PYTHON_IMG=python:3.11-slim
ARG NODE_IMG=node:20-slim
ARG NGINX_IMG=nginx:1.27-alpine

# ---------- 前端构建阶段：esbuild 把 src/ 打包为 dist/i18n.js 与 dist/graph_engine.js ----------
FROM ${NODE_IMG} AS nodebuilder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY src ./src
RUN npm run build

# ---------- 页面构建阶段：python 生成全部静态页 ----------
FROM ${PYTHON_IMG} AS builder
WORKDIR /src
# 前端产物已由 nodebuilder 阶段生成，跳过 Python 阶段内的 esbuild（避免重复装 Node 依赖）
ENV SKIP_NODE_BUILD=1
COPY . .
# 复制 esbuild 已打包的前端产物（graph_engine.js / i18n.js）；其余 dist/* 由 COPY . . 带入
COPY --from=nodebuilder /app/dist/i18n.js dist/i18n.js
COPY --from=nodebuilder /app/dist/graph_engine.js dist/graph_engine.js
# 项目零第三方依赖（仅 Python 标准库 + 内部模块）
RUN python3 build_all.py

# ---------- 运行阶段：用 nginx 提供静态站点 ----------
FROM ${NGINX_IMG} AS runtime
# 用自定义配置替换默认配置
RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/app.conf

# 复制构建产物，保持仓库相对目录结构（四页互跳深链依赖该结构）
COPY --from=builder /src/index.html /usr/share/nginx/html/index.html
COPY --from=builder /src/dist /usr/share/nginx/html/dist
COPY --from=builder /src/tools/visualizations /usr/share/nginx/html/tools/visualizations

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1
