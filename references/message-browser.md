---
name: bilibili-message
version: 1.0.0
author: entrence
description: B站私信发送。通过浏览器注入Cookie操作私信UI（api.vc域名从服务器IP被风控，只能走浏览器）。
---

# B站私信发送

## 触发条件

用户要求给某个B站用户发私信/私聊。
- "给XXX发私信：YYY"
- "私聊XXX说YYY"

## 核心约束

**api.vc.bilibili.com 域名从服务器 IP 被全面风控**，curl 和浏览器内 XHR/fetch 调用都返回 HTML 404 错误页。无法用纯 API 发私信。

唯一可行方案：**浏览器注入 Cookie → 用户空间页点"发消息" → 私信窗口输入并发送**。

## 依赖

- Cookie 文件 `~/.bilibili-cookie`（格式: `SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx`）
- browser 工具（browser_navigate, browser_console, browser_click, browser_snapshot）
- bilibili-cookie skill（Cookie 过期时重新登录）

## 完整流程

### Step 1: 查找目标用户 mid

如果用户只给了昵称没给 mid，先搜索：

```bash
COOKIE=$(cat ~/.bilibili-cookie)
# 用 wbi 搜索接口（注意：不是 /x/web-interface/search/type，是 /x/web-interface/wbi/search/type）
curl -s "https://api.bilibili.com/x/web-interface/wbi/search/type?search_type=bili_user&keyword=<URL编码的昵称>&page=1&page_size=20" \
  -b "$COOKIE" \
  -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  -H "Referer: https://search.bilibili.com/" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); [print(f'{u[\"uname\"]} mid={u[\"mid\"]}') for u in d.get('data',{}).get('result',[])]"
```

注意：搜索接口用 `/x/web-interface/wbi/search/type`，不是 `/x/web-interface/search/type`（后者被风控返回 HTML 错误页）。

如果用户给了 mid 直接跳到 Step 2。

### Step 2: 浏览器注入 Cookie 并导航到用户空间

```
browser_navigate: https://message.bilibili.com/
```

页面会跳转到登录页。用 browser_console 注入 Cookie：

```javascript
document.cookie = "SESSDATA=<SESSDATA值>; path=/; domain=.bilibili.com";
document.cookie = "bili_jct=<bili_jct值>; path=/; domain=.bilibili.com";
document.cookie = "DedeUserID=<DedeUserID值>; path=/; domain=.bilibili.com";
location.reload();
```

从 `~/.bilibili-cookie` 读取这三个值。

### Step 3: 导航到目标用户空间，点击"发消息"

```
browser_navigate: https://space.bilibili.com/<mid>
```

在 snapshot 中找到 `link "发消息"` 的 ref（通常在用户名旁边），用 browser_click 点击它。

点击后会跳转到 `https://message.bilibili.com/#/whisper/mid<目标mid>`，私信窗口自动打开，显示与该用户的聊天记录。

### Step 4: 在私信输入框输入内容

私信输入框是一个 contenteditable 的富文本编辑器，class 为 `brt-editor`：

```javascript
// 2026-10实测: innerText+dispatchEvent 已失效（发送按钮保持 disabled, Vue 状态不认）
// 必须用 execCommand insertText 模拟真实键入:
var editor = document.querySelector('.brt-editor');
editor.focus();
document.execCommand('selectAll', false, null);
document.execCommand('delete', false, null);                    // 清空旧内容
document.execCommand('insertText', false, '<私信内容>');        // 走真实输入通道
// 验证: 发送按钮 class 含 _IsDisabled_ 说明没写入成功, 含 insertText 后变激活
```

### Step 5: 点击发送按钮

发送按钮是一个 div，class 包含 `_MessageSendBox__SendBtn_`：

```javascript
var sendBtn = document.querySelector('[class*="_MessageSendBox__SendBtn_"]');
sendBtn.click();
```

### Step 6: 验证发送成功

检查页面文本中是否出现刚发送的消息：

```javascript
var bodyText = document.body.innerText;
var found = bodyText.indexOf('<私信内容>') >= 0;
// 聊天记录顶部应该显示 "今天 HH:MM" + 消息内容
```

## 关键元素选择器（可能随前端改版变化）

| 元素 | 选择器 | 说明 |
|------|--------|------|
| 私信输入框 | `div.brt-editor` | contenteditable 富文本编辑器 |
| 发送按钮 | `div[class*="_MessageSendBox__SendBtn_"]` | CSS Modules 生成的 class，hash 部分会变 |
| "发消息"链接 | 用户空间页 `link "发消息"` | 在 snapshot 中找 ref |

如果选择器失效，用 browser_console 搜索：
```javascript
// 找输入框
document.querySelectorAll('textarea, [contenteditable], .brt-editor')
// 找发送按钮（搜索包含"发送"文字的元素）
document.querySelectorAll('*').forEach(el => { if(el.children.length===0 && el.innerText==='发送') console.log(el.tagName, el.className) })
```

## Pitfalls

1. **api.vc.bilibili.com 被风控**：从服务器 IP curl 返回 HTML 错误页（非 JSON），浏览器内 XHR 返回 404。不要尝试纯 API 方案。
2. **搜索接口路径**：用 `/x/web-interface/wbi/search/type`，不是 `/x/web-interface/search/type`。后者被风控。
3. **Cookie 注入必须在 bilibili 域名下**：先 navigate 到 bilibili.com 任意页面再注入，否则 document.cookie 设置无效。
4. **富文本编辑器必须用 execCommand insertText**（2026-10实测更新）：`editor.innerText = '...'` + dispatchEvent(input/change) 已失效——内容虽显示但 Vue 状态未同步，发送按钮保持 `_IsDisabled_`。正确姿势：`editor.focus(); document.execCommand('insertText', false, '内容')`，按钮立即激活。清空旧内容用 `selectAll` + `delete` 两个 execCommand。
5. **发送按钮 class 含 hash**：`_MessageSendBox__SendBtn_1izxa_69` 中的 `1izxa_69` 是构建时生成的 hash，会变。用 `[class*="_MessageSendBox__SendBtn_"]` 模糊匹配。
5b. **点击前检查 `_IsDisabled_`**：发送按钮 class 含 `_IsDisabled_` 时点击无效（不报错但消息不发）。用 execCommand insertText 写入后按钮自动激活再点击，并在点击后验证：消息出现在 `document.body.innerText` 中、编辑器清空、按钮回到 disabled。缺失任一即为发送失败。
6. **未关注用户限制**：对方未关注你时，B站提示"对方主动回复或关注你前，最多发送1条消息"。这不是错误，消息仍能发送。
7. **消息内容长度限制**：500字符。

## 关联 Skill

- `bilibili-cookie`: Cookie 获取与刷新。本 skill 依赖其产出的 `~/.bilibili-cookie` 文件。
- `bilibili-comment`: 视频评论发布（纯 API，不受风控影响）。
