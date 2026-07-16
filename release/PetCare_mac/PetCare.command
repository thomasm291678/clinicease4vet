#!/bin/bash
# ======================================================
#  PetCare 宠物医院管理系统 — Mac 双击启动
#  第一次会自动安装依赖，以后直接启动
# ======================================================
clear
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo ""
echo "============================================"
echo "  PetCare 宠物医院管理系统 v2.2"
echo "============================================"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "❌ 未检测到 Python3"
    echo "   请先去 https://www.python.org/downloads/ 下载安装"
    echo "   安装完成后重新双击 PetCare.command"
    read -p "按回车退出..." _
    exit 1
fi

# Install deps if not yet installed
if python3 -c "import flask" 2>/dev/null; then
    echo "✅ 依赖已安装，直接启动..."
else
    echo "🔧 首次运行，正在安装依赖（约 2-5 分钟）..."
    echo ""

    if ! xcode-select -p &>/dev/null; then
        xcode-select --install 2>/dev/null || true
        echo "   请在弹窗中点击安装 Xcode Command Line Tools"
        echo "   安装完成后，重新双击 PetCare.command"
        read -p "按回车退出..." _
        exit 0
    fi

    python3 -m pip install --no-index --find-links "$DIR/wheels" \
        Flask==3.0.3 flask-cors==6.0.5 PyJWT==2.9.0 bcrypt==4.2.0 \
        cryptography==43.0.1 requests==2.34.0 PyMuPDF==1.26.0 \
        sentence-transformers==5.6.0 faiss-cpu==1.10.0 numpy==1.26.4 \
        scikit-learn scipy 2>&1 | tail -3

    echo ""
    echo "✅ 安装完成！"
fi

# Start
export HF_HOME="$DIR/data/knowledge_base/models"
export HF_HUB_OFFLINE=1
export DEBUG=false

echo ""
echo "  正在初始化数据库..."
echo "  正在加载 RAG 知识库..."
echo ""
echo "  🌐 浏览器访问: http://localhost:5000"
echo "  🛑 关闭系统: 关闭这个窗口即可"
echo ""

sleep 1
open http://localhost:5000 2>/dev/null || true

python3 app.py
