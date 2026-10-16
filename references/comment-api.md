---
name: bilibili-comment
version: 1.0.0
author: entrence
description: B站视频评论发布（一级评论+回复评论）。读取已存储Cookie, 调用reply/add接口。
---

# B站视频评论发布

## 触发条件

用户要求在B站视频下方发表评论、回复评论。

典型场景:
- "在 BVxxxxxxxx 视频底下评论 XXX"
- "回复这条评论"
- "给这个视频发个弹幕评论"（注意：弹幕和评论是两回事，弹幕用 danmu 接口，本skill只管评论reply）

## 依赖

- Cookie 文件 `~/.bilibili-cookie`（格式: `SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx`）
- 如果 Cookie 过期（返回 -101），Cookie过期, 按 references/cookie-login.md 重新扫码登录

## 快速用法（脚本）

```bash
bash ~/.hermes/skills/bilibili/scripts/post_reply.sh <BVID> <message> [root_rpid] [parent_rpid]
```

- 一级评论: 只传 BVID 和 message
- 回复评论: 额外传 root_rpid（根评论rpid），parent_rpid 可选（默认=root_rpid）

## 典型工作流

A. **发一级评论**: BVID + message → 直接调 post_reply.sh
B. **回复某人的评论**: 先拉评论列表找到目标用户的 rpid, 再用 post_reply.sh 传 root_rpid
C. **删除自己发的评论**: 用 reply/del 接口 (见 references/api.md)

## 手动流程

### Step 0: 读取 Cookie

```python
cookie = open('/home/ubuntu/.bilibili-cookie').read().strip()
# 解析 SESSDATA 和 bili_jct
```

### Step 1: BVID -> AID

```bash
curl -s "https://api.bilibili.com/x/web-interface/view?bvid=${BVID}" -b "$COOKIE" \
  -H "User-Agent: Mozilla/5.0 ..." | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['aid'])"
```

### Step 2: 查找目标评论 rpid（回复评论时需要）

回复某人的评论前，必须先拿到他评论的 rpid。拉取评论列表搜索:

```
GET https://api.bilibili.com/x/v2/reply/main?type=1&oid={AID}&mode=3&next=0&ps=30
```

- mode=3 按热度排序, mode=2 按时间排序
- next=0 第一页, 翻页用上一页返回的 cursor
- ps=每页条数 (默认30)

返回 `data.replies[]`, 每条含:
  - `member.uname` / `member.mid` — 评论者
  - `rpid` — 评论ID（回复时传这个）
  - `content.message` — 评论内容
  - `like` — 点赞数
  - `replies[]` — 子回复

遍历找到目标用户名后取其 rpid, 传给 post_reply.sh 的第三个参数。

### Step 3: POST 评论

```
POST https://api.bilibili.com/x/v2/reply/add
Content-Type: application/x-www-form-urlencoded
Cookie: SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx
Referer: https://www.bilibili.com/video/{BVID}
Origin: https://www.bilibili.com

参数（form-urlencoded）:
  oid      = {AID}          # 视频的 avid
  type     = 1              # 1=视频, 12=专栏, 11=动态
  message  = {评论内容}
  platf    = 1              # 平台标志, 固定1
  root     = {root_rpid}    # 回复评论时传根评论rpid, 一级评论传0或不传
  parent   = {parent_rpid}  # 回复评论时传父评论rpid, 一级评论传0或不传
  csrf     = {bili_jct}     # CSRF token = bili_jct 的值
```

### Step 4: 校验返回

成功: `code=0, message=OK`, 返回 `data.rpid`（新评论的rpid）, `data.reply.content.message` 确认内容。

### Step 5: 删除评论（测试清理用）

```
POST https://api.bilibili.com/x/v2/reply/del
参数: oid={AID}, type=1, rpid={要删的rpid}, csrf={bili_jct}
```

返回 `code=0, message=OK` 即删除成功。只能删自己发的评论。

详细 API 参数、错误码、评论列表接口见 `references/api.md`。

失败码:
- `-101` 账号未登录 → Cookie过期, 按 references/cookie-login.md 重新扫码登录
- `-403` 权限不足
- `-509` 请求过于频繁 → 等几秒重试
| -635 | 该视频不允许发布评论 |
| -636 | 发送的数据不合法 |
- `-637` 系统禁止的信息（含敏感词）
- `12015` 内容长度超限（1-1000字符）
- `12061` UP主已关闭评论区
| 12061 | UP主已关闭评论区 |

## 查找用户最新视频

用户的典型需求：去某人的最新视频下评论。需要先用 API 拿到 BVID 才能调 post_reply.sh。

接口可靠性排序（服务器 IP + Cookie）:

- 可用: `/x/web-interface/wbi/search/type?search_type=video&keyword=<用户名>&order=pubdate` — 按发布时间排序，取第一条即为最新视频。返回 bvid/aid/title/pubdate
- 可用: `/x/web-interface/wbi/search/type?search_type=bili_user&keyword=<用户名>` — 找用户 mid
- 可用: `/x/web-interface/view?bvid=<BVID>` — BVID→AID 转换，一直稳定
- 可用: `/x/v2/reply/main?type=1&oid=<AID>&mode=3` — 评论列表，mode=3热度/2时间
- 可用: `/x/v2/reply/del` — 删除评论，POST 参数 oid/type/rpid/csrf
- -799 限流: `/x/space/arc/search?mid=<MID>&order=pubdate` — 服务器 IP 被限流，重试无效
- -403 需 wbi 签名: `/x/space/wbi/arc/search?mid=<MID>` — 需计算 w_rid/wbi_sign，复杂

推荐方案：用搜索接口按用户名搜视频（search_type=video），不需要 wbi 签名，返回按时间排序的视频列表。

```bash
COOKIE=$(cat ~/.bilibili-cookie)
KEYWORD=$(python3 -c "import urllib.parse; print(urllib.parse.quote('科比拉姆'))")
curl -s "https://api.bilibili.com/x/web-interface/wbi/search/type?search_type=video&keyword=${KEYWORD}&order=pubdate&page=1&page_size=5" \
  -b "$COOKIE" \
  -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  -H "Referer: https://search.bilibili.com/" \
  | python3 -c "import sys,json,re; d=json.load(sys.stdin); [print(f'BVID={v[\"bvid\"]} aid={v[\"aid\"]} 标题={re.sub(\"<[^>]+>\",\"\",v[\"title\"])[:50]}') for v in d.get('data',{}).get('result',[])]"
```

## 关键约束

1. **必须带 Referer 和 Origin 头**: 缺少会返回 -101/-403
2. **csrf = bili_jct**: POST 必须带 csrf 参数, 值等于 bili_jct cookie 的值
3. **oid 是 avid 不是 bvid**: 先把 BVID 转成 AID 再传
4. **type=1 是视频**: 专栏=12, 动态=11, 不要搞混
5. **回复评论需要 root+parent**: root=根评论rpid, parent=被回复评论rpid; 一级评论 root=0 parent=0
6. **API 优先，浏览器兜底**: B站 API 从服务器 IP 调用时常遇风控/限流。遇到某接口不可用时，先尝试其他 API 路径（如搜视频用 wbi/search 而非 space/arc），仅当所有 API 路径都走不通才用浏览器。用户明确不喜欢用浏览器获取 API 数据。

## Pitfalls

1. **忘记 csrf 参数**: POST body 必须包含 `csrf={bili_jct}`, 否则返回 -101
2. **oid 类型错误**: 传了 bvid 而非 avid, 返回错误。必须先 view 接口转换
3. **评论内容需 urlencode**: 含中文/特殊字符必须 `--data-urlencode`
4. **频繁评论被风控**: 短时间多次评论返回 -509, 等 5-10 秒重试
5. **敏感词过滤**: B站会拦截部分内容返回 -637, 内容需文明
6. **Cookie 字符串格式**: `~/.bilibili-cookie` 是 `SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx` 单行格式, curl -b 直接用
7. **风控可能需要完整 UA**: 简短 UA 可能被拦截, 用完整 Chrome UA 字符串

## 关联 Skill

- `bilibili-cookie`: Cookie 获取与刷新。本 skill 依赖其产出的 `~/.bilibili-cookie` 文件。Cookie 过期时切换到该 skill 重新登录。
