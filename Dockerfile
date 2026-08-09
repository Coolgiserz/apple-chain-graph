# syntax=docker/dockerfile:1

# ---------- 构建阶段：生成全部静态页面 ----------
# 项目零第三方依赖（仅 Python 标准库 + 内部模块），用官方 python 镜像跑 build_all.py
FROM python:3.11-slim AS builder
WORKDIR /src
COPY . .
RUN python3 build_all.py

# ---------- 运行阶段：用 nginx 提供静态站点 ----------
FROM nginx:1.27-alpine AS runtime
# 用自定义配置替换默认配置
RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/app.conf

# 复制构建产物，保持仓库相对目录结构（四页互跳的深链依赖该结构）
COPY --from=builder /src/index.html /usr/share/nginx/html/index.html
COPY --from=builder /src/dist /usr/share/nginx/html/dist
COPY --from=builder /src/tools/visualizations /usr/share/nginx/html/tools/visualizations

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1
