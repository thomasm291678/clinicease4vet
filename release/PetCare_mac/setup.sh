#!/bin/bash
# ======================================================
#  PetCare 宠物医院管理系统 - Mac 离线安装脚本
# ======================================================
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo ""
echo "============================================"
echo "  PetCare 离线环境配置"
echo "============================================"
echo ""

# 1. Check Python
if ! command -v python3 &>/dev/null; then
    echo "[错误] 未检测到 Python3，请先安装 Python 3.9+"
    echo "  https://www.python.org/downloads/"
    exit 1
fi

PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "[1/4] Python 版本: $PYVER"

# 2. Check Xcode Command Line Tools
echo "[2/4] 检查编译工具..."
if ! xcode-select -p &>/dev/null; then
    echo "  需要 Xcode Command Line Tools 编译 scikit-learn/scipy"
    echo "  请在弹窗中点击安装..."
    xcode-select --install 2>/dev/null || true
    echo "  完成后按 Enter 继续..."
    read -r
fi

# 3. Install all pip packages from local wheels
echo "[3/4] 安装 Python 依赖 (离线, 约需 2-5 分钟)..."
python3 -m pip install --no-index --find-links "$DIR/wheels" \
    Flask==3.0.3 flask-cors==6.0.5 PyJWT==2.9.0 bcrypt==4.2.0 \
    cryptography==43.0.1 requests==2.34.0 PyMuPDF==1.26.0 \
    sentence-transformers==5.6.0 faiss-cpu==1.10.0 numpy==1.26.4 \
    scikit-learn scipy 2>&1 | tail -5

echo "[4/4] 依赖安装完成!"
echo ""
echo "  运行 ./start.sh 启动系统"
echo "============================================"
