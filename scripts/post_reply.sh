#!/usr/bin/env bash
# B站视频评论发布脚本
# 用法: post_reply.sh <BVID> <message> [root_rpid] [parent_rpid]
#   BVID        视频 BV号 (如 BV1MTbY6UEFt)
#   message     评论内容
#   root_rpid   回复根评论的rpid (回复评论时传, 发一级评论留空或0)
#   parent_rpid 回复父评论的rpid (回复评论时传, 留空则=root_rpid)
#
# 依赖: ~/.bilibili-cookie (SESSDATA + bili_jct + DedeUserID)
# 示例:
#   一级评论:  post_reply.sh BV1MTbY6UEFt "666"
#   回复评论:  post_reply.sh BV1MTbY6UEFt "说得好" 310871061105
set -euo pipefail

BVID="${1:?用法: post_reply.sh <BVID> <message> [root_rpid] [parent_rpid]}"
MESSAGE="${2:?评论内容不能为空}"
ROOT_RPID="${3:-0}"
PARENT_RPID="${4:-$ROOT_RPID}"

COOKIE_FILE="${HOME}/.bilibili-cookie"
if [[ ! -f "$COOKIE_FILE" ]]; then
  echo "错误: Cookie 文件不存在: $COOKIE_FILE"
  echo "请先用 bilibili-cookie skill 二维码登录获取 Cookie"
  exit 1
fi

COOKIE=$(cat "$COOKIE_FILE")
SESSDATA=$(echo "$COOKIE" | grep -oP 'SESSDATA=\K[^;]+')
BILI_JCT=$(echo "$COOKIE" | grep -oP 'bili_jct=\K[^;]+')

if [[ -z "$SESSDATA" ]]; then
  echo "错误: SESSDATA 为空, Cookie 可能已过期"
  echo "请用 bilibili-cookie skill 重新扫码登录"
  exit 1
fi
if [[ -z "$BILI_JCT" ]]; then
  echo "错误: bili_jct 为空"
  exit 1
fi

UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Step 1: BVID -> AID
echo "正在获取视频信息: ${BVID}..."
INFO=$(curl -s "https://api.bilibili.com/x/web-interface/view?bvid=${BVID}" \
  -b "$COOKIE" \
  -H "User-Agent: ${UA}")

AID=$(echo "$INFO" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(1) if d.get('code')!=0 else print(d['data']['aid'])") || {
  echo "BVID -> AID 转换失败, 检查 BVID 是否正确"
  exit 1
}
echo "  aid=${AID}"

# Step 2: 发评论
echo "正在发送评论..."
RESP=$(curl -s -X POST "https://api.bilibili.com/x/v2/reply/add" \
  -b "$COOKIE" \
  -H "User-Agent: ${UA}" \
  -H "Referer: https://www.bilibili.com/video/${BVID}" \
  -H "Origin: https://www.bilibili.com" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "oid=${AID}" \
  --data-urlencode "type=1" \
  --data-urlencode "message=${MESSAGE}" \
  --data-urlencode "platf=1" \
  --data-urlencode "root=${ROOT_RPID}" \
  --data-urlencode "parent=${PARENT_RPID}" \
  --data-urlencode "csrf=${BILI_JCT}")

# Step 3: 解析结果 (用 stdin 传 JSON 避免引号转义问题)
echo "$RESP" | python3 -c "
import sys, json
resp = json.load(sys.stdin)
code = resp.get('code', '?')
msg = resp.get('message', '?')
bvid = '${BVID}'
aid = '${AID}'
root_rpid = '${ROOT_RPID}'
if code == 0:
    data = resp['data']
    rpid = data.get('rpid', '?')
    content = data.get('reply', {}).get('content', {}).get('message', '?')
    print('评论发送成功!')
    print(f'  视频: {bvid} (aid={aid})')
    print(f'  内容: {content}')
    print(f'  rpid: {rpid}')
    if root_rpid != '0':
        print(f'  回复目标 rpid: {root_rpid}')
else:
    print(f'评论发送失败: code={code} message={msg}')
    if code == -101:
        print('  Cookie 已过期, 请用 bilibili-cookie skill 重新登录')
    elif code == -509:
        print('  请求过于频繁, 等 5-10 秒后重试')
    elif code == -637:
        print('  含敏感词, 修改内容后重试')
    sys.exit(1)
"
