#!/bin/bash
# 部署到服务器 8.145.39.17
# 使用方法: ./deploy.sh

SERVER="8.145.39.17"
REMOTE_DIR="/opt/wechat-ai-editor"

echo "=== 打包项目 ==="
cd "$(dirname "$0")"

# Replace symlink with real files for deployment
rm -f backend/assets
cp -rL "/home/user/code/6-6-1/微信公众号内容生成与排版AI员工/asset" backend/assets

tar --exclude='node_modules' --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' -czf /tmp/wechat-deploy.tar.gz backend/ docker-compose.yml

echo "=== 上传到服务器 ==="
scp /tmp/wechat-deploy.tar.gz root@${SERVER}:${REMOTE_DIR}/ 2>/dev/null || scp /tmp/wechat-deploy.tar.gz root@${SERVER}:/tmp/

echo "=== 服务器部署 ==="
ssh root@${SERVER} << 'ENDSSH'
  mkdir -p /opt/wechat-ai-editor
  cd /opt/wechat-ai-editor
  tar -xzf /tmp/wechat-deploy.tar.gz -C . 2>/dev/null || tar -xzf /tmp/wechat-deploy.tar.gz

  # Build and start
  cd /opt/wechat-ai-editor
  docker compose up -d --build

  echo "=== 部署完成 ==="
  docker compose ps
ENDSSH

echo "=== 后端地址: http://${SERVER}:8000 ==="
echo "请在 Vercel 环境变量中设置 VITE_API_BASE_URL=http://${SERVER}:8000"
