#!/bin/bash
# 阿里云部署打包脚本
# 用法: ./aliyun-package.sh
# 作用: 打包后端代码 + assets + docker-compose + 初始化脚本
# 输出: /tmp/backend-deploy.tar.gz

set -e

cd "$(dirname "$0")"
PROJECT_ROOT=$(pwd)
echo "=== 打包项目 (${PROJECT_ROOT}) ==="

# 1. Ensure assets are real files (not symlinks)
if [ -L "backend/assets" ]; then
    echo "[注意] assets 是符号链接，需要替换为实际文件..."
    echo "       请先手动复制实际文件到 backend/assets/"
    echo "       例如: cp -rL /path/to/asset/src backend/assets"
    exit 1
fi

if [ ! -d "backend/assets" ] || [ -z "$(ls -A backend/assets 2>/dev/null)" ]; then
    echo "[错误] backend/assets 目录为空或不存在!"
    exit 1
fi

# 2. Clean up cache files
find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find backend -type f -name '*.pyc' -delete 2>/dev/null || true

# 3. Package
# Exclude: __pycache__, .pyc, node_modules (just in case), large dev files
tar --exclude='__pycache__' --exclude='*.pyc' \
    -czf /tmp/backend-deploy.tar.gz \
    backend/ \
    docker-compose.yml \
    ecs-init.sh

echo "=== 打包完成 ==="
echo "包路径: /tmp/backend-deploy.tar.gz"
echo "包大小: $(du -h /tmp/backend-deploy.tar.gz | cut -f1)"
echo ""
echo "=== 部署步骤 ==="
echo ""
echo "1. 登录阿里云 ECS 控制台，创建实例（推荐 Ubuntu 24.04）"
echo "   安全组开放端口: 22, 8000"
echo ""
echo "2. 上传到 ECS:"
echo "   scp /tmp/backend-deploy.tar.gz root@<ECS公网IP>:/opt/"
echo ""
echo "3. SSH 登录 ECS:"
echo "   ssh root@<ECS公网IP>"
echo ""
echo "4. 解压并部署:"
echo "   cd /opt"
echo "   tar -xzf backend-deploy.tar.gz"
echo "   cd wechat-ai-editor"
echo "   bash ecs-init.sh   # 会自动安装 Docker + 构建 + 启动"
echo ""
echo "5. 编辑配置:"
echo "   nano .env   # 填写 LLM_API_KEY / WECHAT_APP_ID / WECHAT_APP_SECRET"
echo "   bash ecs-init.sh   # 再次运行以启动"
echo ""
echo "6. 更新 Vercel 前端环境变量:"
echo "   VITE_API_BASE_URL=http://<ECS公网IP>:8000"
