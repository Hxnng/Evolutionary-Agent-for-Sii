#!/bin/bash
# Meta-Harness 启动脚本

set -e

echo "Starting Meta-Harness search..."
echo "================================"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found"
    exit 1
fi

# 检查依赖
echo "Checking dependencies..."
pip3 install -q -r requirements.txt

# 运行Meta-Harness
echo "Running Meta-Harness..."
cd "$(dirname "$0")"
python3 meta_loop.py

echo "================================"
echo "Meta-Harness search completed!"
