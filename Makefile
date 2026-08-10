# 常用快捷键（macOS / Linux）
# 需先装好 Docker（含 Compose v2）；本地不想用 Docker 时可用 make serve。
# 前端脚本（src/ 下的 ES Module）由 esbuild 打包，需本机装好 Node ≥ 18 与 npm：
#   make build-frontend   仅用 esbuild 打包 dist/i18n.js 与 dist/graph_engine.js
#   make build-site       前端打包 + python build_all.py 重生成全部静态页
#   make serve            只用 Python 起静态服务器（需先 make build-site 才有最新前端）
#   make dev              build-site + 起本地静态服务器
#
#   make up      构建并后台启动（http://localhost:16161，HTTP）
#   make down    停止并移除容器
#   make up-prod 生产启动（HTTPS，需 ./certs 证书）：叠加 docker-compose.prod.yml
#   make build   仅构建 Docker 镜像
#   make logs    实时查看容器日志
#   make ps      查看运行状态
#   make clean   停止并删除本地镜像

.PHONY: help build build-frontend build-site up down up-prod down-prod logs ps serve dev clean lint lint-js lint-py test test-js test-py validate-data

IMAGE := apple-supply-chain:latest
PORT  := 16161

help:
	@echo "可用快捷键："
	@echo "  make build-frontend  仅 esbuild 打包前端（dist/i18n.js, dist/graph_engine.js）"
	@echo "  make build-site      前端打包 + python build_all.py 重生成全部静态页"
	@echo "  make up              构建并后台启动（HTTP，http://localhost:$(PORT)）"
	@echo "  make down            停止并移除容器"
	@echo "  make up-prod         生产启动（HTTPS，需 ./certs 证书）：叠加 docker-compose.prod.yml"
	@echo "  make down-prod       停止生产容器"
	@echo "  make build           仅构建 Docker 镜像"
	@echo "  make logs            实时查看容器日志"
	@echo "  make ps              查看运行状态"
	@echo "  make serve           不用 Docker，本地起 Python 静态服务器（http://localhost:$(PORT)）"
	@echo "  make dev             build-site + 本地静态服务器"
	@echo "  make clean           停止并删除本地镜像"

build-frontend:
	npm ci
	npm run build

build-site: build-frontend
	python3 build_all.py

build:
	docker build -t $(IMAGE) .

up:
	docker compose up -d --build

down:
	docker compose down

up-prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

down-prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml down

logs:
	docker compose logs -f

ps:
	docker compose ps

serve:
	python3 -m http.server $(PORT)

dev: build-site
	python3 -m http.server $(PORT)

# ---- 质量门禁（团队本地与 CI 共用）----
lint: lint-js lint-py

lint-js:
	npm run lint

lint-py:
	python3 -m flake8 --max-line-length=120 scripts tools

test: test-js test-py validate-data

test-js:
	node tests/engine.test.mjs

test-py:
	python3 -m unittest discover -s tests -p "test_*.py"

validate-data:
	python3 tools/validate_dataset.py

clean:
	docker compose down -v
	-docker rmi -f $(IMAGE)
