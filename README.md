# bilibili

B站（哔哩哔哩）全功能 Hermes skill：Cookie 二维码登录、视频下载、评论发布、自动评论机器人、私信发送、B站日报PPT、弹幕爬取、WBI 搜索。由 6 个独立 skill 合并而成（6合1）。

## Features

- **Cookie 登录**：生成二维码 PNG 扫码获取 Cookie，保存 `~/.bilibili-cookie`
- **视频下载**：yt-dlp 主路线（1080P 需 Cookie 转 Netscape 格式）；412 错误时降级 API+platform=html5 兜底
- **评论发布**：一级评论 + 回复评论（reply/add API），支持自清理验证流程
- **自动评论机器人**：轮询搜索最新视频自动评论，Excel 去重防重复，`--once` 单轮模式
- **私信发送**：api.vc 域名从数据中心 IP 被风控 → 浏览器注入 Cookie 操作消息中心 UI
- **B站日报 PPT**：热门视频 + 全站排行榜 → 统计分析 → 生成 pptx 日报（无需 Cookie）
- **弹幕爬取**：protobuf seg.so 接口，手动 varint 解析（无需 protobuf 库）
- **WBI 搜索**：WBI 签名搜索（视频/用户双模式）

## Install

```
hermes skills install https://raw.githubusercontent.com/entrence/bilibili/main/SKILL.md
```

> 如果 raw.githubusercontent.com 超时，先克隆仓库再把 SKILL.md 放到 `~/.hermes/skills/bilibili/`。

## Prerequisites

### Cookie 准备（核心依赖）

所有需登录功能（评论/私信/下载高清）共用同一 Cookie 文件：

```
~/.bilibili-cookie
格式（单行）: SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx
```

- 通过 skill 的二维码登录流程生成，有效期约 30 天
- 格式非法或过期 → 接口返回 `-101`，重新扫码
- 细节见 `references/cookie-login.md`

### Python 依赖

```
pip3 install openpyxl --break-system-packages   # 自动评论 Excel 记录
```

（日报数据拉取、弹幕解析、WBI 签名均为 Python 标准库实现，无额外依赖）

### Node.js 依赖（仅日报PPT）

```
npm install -g pptxgenjs
export NODE_PATH=$(npm root -g)   # 或按 run_daily.sh 的方式导出
```

### 系统工具

- `yt-dlp`（视频下载主路线）：`pip3 install yt-dlp --user` 或包管理器安装
- `curl`（部分 API 调用演示）
- 有图形环境的浏览器（私信功能用 browser 工具操作 UI）

## Usage

安装后对 Hermes 说：

- 「用B站skill下载这个视频 <URL>」
- 「给这个视频发条评论」
- 「启动自动评论机器人，每5分钟一轮」
- 「给 UP 主 xxx 发条私信」
- 「生成今天的B站日报」
- 「把我的B站 Cookie 刷新一下」/「Cookie 好像过期了」

## Repository Structure

```
bilibili/
├── SKILL.md                      # 路由入口：功能索引 + Cookie约定 + UA规则 + 错误码表
├── references/
│   ├── cookie-login.md           # 二维码登录全流程（含假成功、轮询等7个坑）
│   ├── video-download.md         # yt-dlp + API 双路线
│   ├── comment-api.md            # 评论发布 API
│   ├── reply-api.md              # reply/add、reply/del 接口细节
│   ├── auto-comment.md           # 自动评论机器人
│   ├── message-browser.md        # 私信（浏览器UI路线）
│   ├── daily-report.md           # B站日报 PPT 生成
│   ├── danmaku-protobuf.md       # 弹幕爬取（protobuf 手动解析）
│   ├── APIv2.popular.md          # 热门视频 API
│   ├── APIv2.ranking.md          # 排行榜 API
│   └── verification.md           # 10项功能健康检查清单
└── scripts/
    ├── bili_wbi_search.py        # WBI 搜索（video/bili_user 模式）
    ├── cookie_to_netscape.py     # Cookie → Netscape 格式（yt-dlp 用）
    ├── post_reply.sh             # 发布评论
    ├── bili_auto_comment.py      # 自动评论机器人（--once 单轮）
    ├── fetch_data.py             # 日报数据拉取
    ├── gen_pptx.js               # 日报 PPT 生成（pptxgenjs）
    └── run_daily.sh              # 日报一键脚本
```

## Notes（重要坑）

1. **私信 api.vc 域名被风控**：从数据中心/服务器 IP 调 api.vc 会被拒，只能走浏览器注入 Cookie 操作消息中心 UI。
2. **412 错误**：yt-dlp 下载被拒时改用 API 路线 `playurl?platform=html5`，必带 `Referer: https://www.bilibili.com`。
3. **私信编辑器注入**（2026-10 实测）：`innerText + dispatchEvent` 已失效，必须 `document.execCommand('insertText')`，且发送按钮 class 含 `_IsDisabled_` 时点击无效。
4. **弹幕空 segment 返回 HTTP 304**（不是空数据），urllib 抛 HTTPError，try/except 跳过即可，不代表失败。
5. **Cookie 有效期约 30 天**，接口返回 `-101` 即过期，重新扫码。测试/自检一律用自己的号，自清理测试评论。
6. 路径均已环境感知（`~` / homedir），无 `/home/ubuntu` 硬编码。

## License

MIT
