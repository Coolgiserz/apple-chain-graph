# 多阶段构建：python 生成静态页 -> nginx 托管
# 镜像源可经 .env 覆盖为完整镜像名（推荐做法，官方源与镜像源都能正确解析）：
#   PYTHON_IMG=swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.11-slim
#   NGINX_IMG=swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/nginx:1.27-alpine
# 留空 / 不设 .env 时走官方源 python:3.11-slim / nginx:1.27-alpine（docker.io 官方仓库）。
ARG PYTHON_IMG=python:3.11-slim
ARG NGINX_IMG=nginx:1.27-alpine

# ---------- 构建阶段：生成全部静态页面 ----------
FROM ${PYTHON_IMG} AS builder
WORKDIR /src
COPY . .
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
