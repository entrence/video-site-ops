#!/bin/bash
# B站日报一键生成（母本在 ~/.hermes/skills/bilibili/scripts/，数据与PPT输出到 ~/bilibili-daily/）
# 输出: ~/bilibili-daily/B站日报_YYYY-MM-DD.pptx
set -e

SCRIPT_DIR="~/.hermes/skills/bilibili/scripts"
DIR="~/bilibili-daily"
mkdir -p "$DIR"

echo "[1/2] 拉取数据..."
python3 "$SCRIPT_DIR/fetch_data.py"

echo "[2/2] 生成PPT..."
export NODE_PATH=~/.npm-global/lib/node_modules
node "$SCRIPT_DIR/gen_pptx.js"

LATEST=$(ls -t "$DIR"/B站日报_*.pptx | head -1)
echo "完成: $LATEST"
