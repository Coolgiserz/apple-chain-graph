# 多阶段构建：node 打包前端 -> python 生成静态页 -> nginx 托管
# 镜像源可经 .env 覆盖为完整镜像名（推荐做法，官方源与镜像源都能正确解析）：
#   PYTHON_IMG=swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.13-slim-bookworm-linuxarm64
#   NODE_IMG=swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/node:24-slim-linuxarm64
#   NGINX_IMG=swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/nginx:1.29.8-alpine3.23-linuxarm64
# 留空 / 不设 .env 时走官方源 python:3.13-slim / node:24-slim / nginx:1.27-alpine（docker.io 官方仓库）。
ARG PYTHON_IMG=python:3.13-slim
ARG NODE_IMG=node:24-slim
ARG NGINX_IMG=nginx:1.27-alpine

# ---------- 前端构建阶段：esbuild 把 src/ 打包为 dist/i18n.js 与 dist/graph_engine.js ----------
FROM ${NODE_IMG} AS nodebuilder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY src ./src
# scripts/build_locales.mjs 是语言包生成 + i18n 审计的唯一实现（Node），由 npm run build 调用；
# 它需读取 locales/*.json 与扫描 src/engine、src/lib，故一并 COPY 进本阶段。
COPY locales ./locales
COPY scripts ./scripts
RUN npm run build

# ---------- 页面构建阶段：python 生成全部静态页 ----------
FROM ${PYTHON_IMG} AS builder
WORKDIR /src
# 前端产物已由 nodebuilder 阶段生成，跳过 Python 阶段内的 esbuild（避免重复装 Node 依赖）
ENV SKIP_NODE_BUILD=1
COPY . .
# 复制 esbuild 已打包的前端产物（graph_engine.js / i18n.js / locales.js）；
# 语言包 dist/locales.js 由 nodebuilder 阶段的 scripts/build_locales.mjs 生成（含 i18n 审计）。
COPY --from=nodebuilder /app/dist/i18n.js dist/i18n.js
COPY --from=nodebuilder /app/dist/graph_engine.js dist/graph_engine.js
COPY --from=nodebuilder /app/dist/locales.js dist/locales.js
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
# 时效数据 feed：前端 DataLayer 运行时 fetch data/feeds/*.json（风险/估值/舆情），
# 必须由 build_all.py 生成并随镜像发布，否则首页新鲜度徽标会 404（pages.yml 仅服务 GitHub Pages 路径）。
COPY --from=builder /src/data/feeds /usr/share/nginx/html/data/feeds
# Plan C：首页改为浏览器端 fetch 图数据，故 data/apple_supply_chain.json 必须随镜像发布
# （旧方案是构建期内联进 index.html，无需单独发布）。data/supply_chain_risk.json 为构建期
# 从 tools/output 复制的风险副本，供首页合并「风险视图」字段；缺失则降级（仅缺风险着色）。
COPY --from=builder /src/data/apple_supply_chain.json /usr/share/nginx/html/data/apple_supply_chain.json
COPY --from=builder /src/data/supply_chain_risk.json /usr/share/nginx/html/data/supply_chain_risk.json
# SEO 基础设施（sitemap / robots / OG 封面），与 Pages 发布保持一致
COPY --from=builder /src/sitemap.xml /usr/share/nginx/html/sitemap.xml
COPY --from=builder /src/robots.txt /usr/share/nginx/html/robots.txt
COPY --from=builder /src/assets /usr/share/nginx/html/assets

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1
