#!/bin/bash
# ======================================================
#  PetCare 宠物医院管理系统 - 一键启动
# ======================================================

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo ""
echo "============================================"
echo "  PetCare 宠物医院管理系统 v2.1"
echo "============================================"
echo ""

# Set model cache path to bundled directory
export HF_HOME="$DIR/data/knowledge_base/models"
export HF_HUB_OFFLINE=1
export DEBUG=false

echo "  正在初始化 SQLite 数据库..."
echo "  正在加载 RAG 知识库 (中英双语)..."
echo ""
echo "  >>> 浏览器访问: http://localhost:5000"
echo ""

open http://localhost:5000 2>/dev/null || true

python3 app.py
