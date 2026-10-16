# B站 Skill 全套功能验证（健康检查）

触发：用户说"试一下skill是否正常"——新session重载、合并后、Cookie刷新后都要跑。2026-10-16 合并后首次全套实测提炼（10/10 通过）。

## 原则
- 测试账号：发信方=当前Cookie登录的号（以 nav 实测为准，勿信文档写死的账号）；私信收信方=自己的另一个号（勿打扰陌生人）
- 最小副作用，且透明告知GK：会真实发1条评论"666"（立即删）、自动评论1条"行"（立即删）、给GK自己另一个号发1条"(测试)请忽略"私信——全部只动GK自己的号
- 测试产物放 /tmp/bili_test，跑完删
- 实测与文档不符 → 当场修对应 references（首测就修了3处：私信编辑器写入法/弹幕304/登录账号写死）

## 前置
1. `skill_view(name='bilibili')`
2. `~/.bilibili-cookie` 存在
3. openpyxl 已装，缺则 `pip3 install openpyxl --break-system-packages`

## 10项测试

1. **Cookie/nav**：GET `x/web-interface/nav` 带Cookie → code=0 + uname，记录当前登录账号
2. **WBI搜索**：`python3 ~/.hermes/skills/bilibili/scripts/bili_wbi_search.py "<任意词>" bili_user`（另试 video 模式；顺手为第4项选测试视频：video模式搜任意关键词取一个老短视频）
3. **Netscape转换**：`python3 ~/.hermes/skills/bilibili/scripts/cookie_to_netscape.py` → /tmp/bili_netscape_cookie.txt
4. **评论 add+del 自清理**：view→aid；reply/add message="666"（oid=aid、type=1、platf=1、root=parent=0、csrf=bili_jct、Referer+Origin必带，参数详见 references/reply-api.md）；记 rpid；sleep 2；reply/del → code=0
5. **自动评论机器人**：`ps aux | grep bili_auto_comment | grep -v grep` 确认无残留后，`python3 ~/.hermes/skills/bilibili/scripts/bili_auto_comment.py --once --count 1 --excel /tmp/bili_test/test_auto.xlsx`；从Excel第8列（rpid）取值 → reply/del 清理
6. **弹幕**：view→cid；拉 segment 1..6。**空segment两种形态：<10字节 或 HTTP 304（urllib抛HTTPError），都要 try/except 跳过**；protobuf 手动解析 field 2/3/7（详见 references/danmaku-protobuf.md）
7. **下载 API法**：playurl `qn=16&fnval=0&platform=html5&high_quality=1` → data.durl[0].url 直链 → 带 `Referer: https://www.bilibili.com` 下载（qn=16 仅2-3MB）→ 验证文件头 `ftyp`
8. **下载 yt-dlp法**：`cd /tmp/bili_test && yt-dlp --cookies /tmp/bili_netscape_cookie.txt -o "t.%(ext)s" "https://www.bilibili.com/video/<BVID>"` → 1080P + ftyp（证明 Netscape Cookie 解锁高清）
9. **私信（浏览器）**：bilibili.com → console 注入三Cookie（document.cookie, domain=.bilibili.com）→ space.bilibili.com/<收信方UID> 点"发消息" → `.brt-editor` 用 `document.execCommand('insertText', false, '(测试)请忽略')` 写入（**innerText+dispatchEvent 已失效**）→ 发送按钮 class 无 `_IsDisabled_` 才 click → 验证：消息出现在 body.innerText、编辑器清空、按钮回 disabled（详见 references/message-browser.md）
10. **日报端到端**：`bash ~/.hermes/skills/bilibili/scripts/run_daily.sh` → 数据+PPT出在 /home/ubuntu/bilibili-daily/（副作用：覆盖 data.json + 生成当日pptx，幂等可接受）

## 收尾
`rm -rf /tmp/bili_test`；向GK汇报10项结果 + 当前登录账号 + 发现的文档偏差及已修复项。
