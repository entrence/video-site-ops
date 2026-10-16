---
name: bilibili
version: 1.0.0
author: entrence
description: B站运营全家桶：Cookie二维码登录、视频下载(yt-dlp/API)、评论发布与自动评论机器人、私信发送(浏览器)、热门数据日报PPT、弹幕爬取、视频/用户WBI搜索。任何B站相关任务先加载本skill。
---

# B站运营 Skill（全家桶）

合并自6个原skill：bilibili-cookie / bilibili-comment / bilibili-auto-comment / bilibili-message / bilibili-daily-report / bilibili-video-download。

## Skill-First 铁律

任何B站任务（下载、评论、私信、调API、日报、弹幕）第一步永远是 `skill_view(name='bilibili')`。不要 yt-dlp 裸跑、不要自己写脚本硬调API、不要直接 browser 硬闯。GK 在多个 session 中反复纠正过"不用skill"的问题。

**所有B站请求（下载、API调用、评论）必须带 Cookie**，即使普通清晰度，不带会 412。

## 功能路由

| 任务 | 详细文档 | 脚本/快速命令 |
|------|----------|----------------|
| Cookie 获取/刷新（扫码登录） | references/cookie-login.md | 流程内嵌文档（含完整Python代码） |
| 搜索视频/用户（WBI） | references/cookie-login.md | `scripts/bili_wbi_search.py "<关键词>" [video\|bili_user]` |
| 视频下载 | references/video-download.md + references/cookie-login.md 的 yt-dlp 节 | `scripts/cookie_to_netscape.py` → yt-dlp |
| 发/回复/删评论 | references/comment-api.md | `scripts/post_reply.sh <BVID> <message> [root_rpid] [parent_rpid]` |
| 自动评论机器人 | references/auto-comment.md | `scripts/bili_auto_comment.py --count 30 --interval 600` |
| 发私信 | references/message-browser.md | 浏览器流程，见文档（api.vc 被风控无法纯API） |
| 热门日报PPT | references/daily-report.md | `bash ~/.hermes/skills/bilibili/scripts/run_daily.sh` |
| 全套功能验证（"试一下skill是否正常"） | references/verification.md | 按文档10项逐项跑，最小副作用 |
| 弹幕爬取 | references/danmaku-protobuf.md | 见文档（protobuf 解析） |
| 热门流/排行榜API | references/APIv2.popular.md, references/APIv2.ranking.md | 公开接口无需登录 |
| 评论API字段/错误码 | references/comment-api.md（附录含原reply API参考） | — |

## 共享基础（所有功能必读）

### Cookie

- 文件：`~/.bilibili-cookie`，单行格式 `SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx`
- SESSDATA=登录凭证（所有需登录接口必带）；bili_jct=csrf token（POST 必带 `csrf=xxx`）；DedeUserID=用户mid
- 有效期约30天。任何接口返回 `-101` 或 nav 显示未登录 → Cookie过期，按 references/cookie-login.md 重新扫码。**主动告知GK"Cookie已过期需重新扫码"，不要等他自己发现**
- 需Cookie操作前先打一次 nav 接口快速验证
- yt-dlp 的 --cookies 只认 Netscape 格式：先跑 `python3 ~/.hermes/skills/bilibili/scripts/cookie_to_netscape.py`（输出 /tmp/bili_netscape_cookie.txt）
- 当前登录账号以 nav 接口 (`x/web-interface/nav`) 实测为准，不要硬编码假设某个UID

### 请求约定

- UA 统一用完整 Chrome 串：`Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36`（简短UA会被风控）
- POST 必带 `Referer: https://www.bilibili.com/video/{BVID}` + `Origin: https://www.bilibili.com` + `csrf`
- 搜索接口必须用 `/x/web-interface/wbi/search/type` 路径（非wbi路径返回HTML错误页）

### API 可靠性总表（服务器IP实测）

| 接口 | 状态 |
|------|------|
| `view`（BVID→AID/CID） | 稳定 |
| `wbi/search/type`（video/bili_user，无需wbi签名） | 可用 |
| `reply/main` / `reply/add` / `reply/del` | 可用 |
| `popular` / `ranking/v2` | 可用，公开无需登录 |
| `space/arc/search` | -799 限流，别用 |
| `search/type`（不带wbi路径） | 风控，返回HTML错误页 |
| `api.vc.bilibili.com`（私信） | 全面风控，只能走浏览器UI |

### 关键错误码

| 码 | 含义 | 处置 |
|----|------|------|
| -101 | 未登录/Cookie失效 | 重新扫码登录 |
| -509 | 请求过于频繁 | 等5-10秒重试 |
| -799 | 服务器IP被限流 | 换接口路径，重试无效 |
| -635 | 视频不允许评论 | 跳过 |
| -637 | 敏感词 | 跳过/改文案 |
| 12014 | 当日评论发送上限已达 | **停脚本等24小时**（不是几小时），勿短间隔重启试探 |
| 412 | 下载不带Cookie/风控 | 带Netscape Cookie或走API法 |
| 12061 | UP主关闭评论区 | 跳过 |

## 各功能一线精华

### 视频下载
yt-dlp + Netscape Cookie 优先（可解锁1080P）。yt-dlp 412 时切API法：playurl 带 `fnval=0&platform=html5` 拿 durl 直链mp4（dash 分离流不登录403），CDN下载必须带 `Referer: https://www.bilibili.com`。qn: 16=360p 32=480p 64=720p 80=1080p。

### 评论
oid 是 **avid 不是 bvid**，先 view 接口转换。一级评论 root=0 parent=0；回复带 root+parent。找用户最新视频：wbi搜索 `search_type=video&order=pubdate` 取第一条。-509 等5-10秒。

### 自动评论机器人
`--count 30 --interval 600`（100/300 会触发12014）。启动前 `ps aux | grep bili_auto_comment` 查残留进程。每条随机延迟1-3秒。持久后台用 `terminal(background=true)` 或 crontab，不用 nohup/disown。大面积12014立即停。

### 私信
api.vc 从服务器IP curl 和页面XHR都不可用。唯一方案：浏览器注入Cookie → 空间页点"发消息" → `.brt-editor` 输入（必须 dispatch input 事件）→ `[class*="_MessageSendBox__SendBtn_"]` 模糊匹配发送。未关注用户限发1条（非错误）。

### 日报
`bash /home/ubuntu/bilibili-daily/run_daily.sh` 一键全流程，无需Cookie，约15秒。脚本母本在本skill scripts/，数据与PPT输出在 /home/ubuntu/bilibili-daily/。pptxgenjs坑：color不带#、option对象每次新建。

## 全局 pitfalls

1. B站请求永远带Cookie，否则412
2. 二维码必须存PNG文件给GK扫码（/home/ubuntu/Downloads/bilibili_qrcode.png），**绝不打印ASCII二维码**
3. 搜索/标题字段含 `<em class="keyword">` 高亮标签，用 `re.sub(r'<[^>]+>', '', title)` 清洗
4. 412/403 时补充 buvid3/buvid4 等Cookie字段应对风控
5. popular/ranking 翻页每页间隔≥1秒防-799
6. 完整分功能 pitfalls 见各 references 文档
