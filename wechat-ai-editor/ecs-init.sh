#!/bin/bash
# ECS 首次部署初始化脚本
# 在阿里云 ECS 上运行: bash ecs-init.sh
set -e

echo "=== 1. 安装 Docker ==="
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | bash
    systemctl enable docker
    systemctl start docker
else
    echo "Docker 已安装"
fi

echo "=== 2. 创建 .env 配置文件 ==="
if [ ! -f .env ]; then
    cat > .env << 'ENVEOF'
# ===========================================
# 微信公众号 AI 编辑器 - 生产环境配置
# ===========================================

# --- LLM API 配置 (已有服务器 8.145.39.17) ---
LLM_API_BASE=http://8.145.39.17:8080/v1
LLM_API_KEY=
LLM_MODEL_NAME=glm-5.1-w8a8

# --- 微信公众平台配置 ---
WECHAT_APP_ID=your_app_id
WECHAT_APP_SECRET=your_app_secret

# --- CORS -- 允许的前端域名 ---
CORS_ORIGINS=https://wechat-ai-editor-hjh.vercel.app
ENVEOF
    echo "已创建 .env 文件，请编辑: nano .env"
    echo "然后输入微信和 LLM 的配置信息"
    exit 1
else
    echo ".env 已存在"
fi

echo "=== 3. 构建并启动 ==="
docker compose build --no-cache
docker compose up -d

echo "=== 4. 等待服务启动 ==="
sleep 5
docker compose ps

# Get public IP
PUBLIC_IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null || curl -s https://api.ipify.org 2>/dev/null || echo "获取IP失败")

echo ""
echo "============================================"
echo "  部署完成!"
echo "============================================"
echo ""
echo "后端地址:     http://${PUBLIC_IP}:8000"
echo "健康检查:     http://${PUBLIC_IP}:8000/api/health"
echo ""
echo "请更新 Vercel 环境变量:"
echo "  VITE_API_BASE_URL=http://${PUBLIC_IP}:8000"
echo ""
echo "常用命令:"
echo "  查看日志:   docker compose logs -f"
echo "  重启:       docker compose restart"
echo "  停止:       docker compose down"
echo "  更新:       git pull && docker compose up -d --build"
echo "============================================"
