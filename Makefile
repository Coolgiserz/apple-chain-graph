# 常用快捷键（macOS / Linux）
# 需先装好 Docker（含 Compose v2）；本地不想用 Docker 时可用 make serve。
#
#   make up      构建并后台启动（http://localhost:8080）
#   make down    停止并移除容器
#   make build   仅构建 Docker 镜像
#   make logs    实时查看容器日志
#   make ps      查看运行状态
#   make serve   不用 Docker，本地起 Python 静态服务器（同端口）
#   make clean   停止并删除本地镜像

.PHONY: help build up down logs ps serve clean

IMAGE := apple-supply-chain:latest
PORT  := 8080

help:
	@echo "可用快捷键："
	@echo "  make up      构建并后台启动（http://localhost:$(PORT)）"
	@echo "  make down    停止并移除容器"
	@echo "  make build   仅构建 Docker 镜像"
	@echo "  make logs    实时查看容器日志"
	@echo "  make ps      查看运行状态"
	@echo "  make serve   不用 Docker，本地起 Python 静态服务器（同端口）"
	@echo "  make clean   停止并删除本地镜像"

build:
	docker build -t $(IMAGE) .

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

serve:
	python3 -m http.server $(PORT)

clean:
	docker compose down -v
	-docker rmi -f $(IMAGE)
