---
name: bilibili-cookie
version: 1.0.0
author: entrence
description: B站二维码登录获取Cookie。生成二维码PNG图片保存到本地目录供用户下载扫描，轮询确认后保存Cookie。
---

# B站 Cookie 获取（二维码登录）

## 触发条件

**所有 B站相关请求**（下载、API 调用、投稿）都必须优先使用已存储的 Cookie，而非仅在需要高清晰度时才用。这是用户的固定要求。

典型场景：
- 下载视频（不带 Cookie 会报 412 Precondition Failed，即使普通清晰度也一样）
- 上传/投稿视频
- 调用需要登录的B站 API
- 之前的 Cookie 过期需要重新获取

## Skill-First 工作流（固定规则）

**任何 B站相关任务（下载视频、发评论、发私信、调API）都必须先加载 `bilibili-cookie` skill。** 不要直接用 yt-dlp 裸跑或自己写 Python 脚本调 API。

用户在多个独立session中反复纠正过这个问题：
- "你用skill啊" (小红书场景，同样的模式)
- "为什么你不用skill" (B站下载视频场景：直接用yt-dlp裸跑报412，又自己写Python脚本硬调API报KeyError，折腾了好几轮才回到skill流程)

B站相关任务的第一步永远是 `skill_view(name='bilibili-cookie')`，而不是自己造轮子。这个规则也适用于所有平台操作任务（小红书、B站等）——先scan skill列表，有对应skill就加载，不要直接browser硬闯或手写API调用。

1. 任何 B站请求前，先检查 `~/.bilibili-cookie` 是否存在
2. 存在则直接使用（yt-dlp 需先转 Netscape 格式，见下方）
3. 如果请求返回 412/403/-101（Cookie 失效），自动触发二维码登录流程
4. 生成二维码 PNG 发给用户扫描，获取新 Cookie 后重试请求

## 关键约束

1. **二维码必须保存为 PNG 图片文件**到用户可访问的目录，告知用户文件路径让他自行下载扫描。
   **绝对不要**在终端打印 ASCII 二维码——终端渲染的二维码可能无法被手机正确识别。
2. Cookie 保存到 `/home/ubuntu/.bilibili-cookie`，格式：`SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx`
3. Cookie 有效期约 30 天，过期后需重新扫码
4. 二维码有效期约 180 秒，超时需重新生成

## 前置依赖

```bash
pip3 install qrcode pillow --break-system-packages
```

## 完整流程

### Step 1: 生成二维码并保存为 PNG

```python
import urllib.request, json, qrcode, os

# 调用B站二维码生成接口
url = 'https://passport.bilibili.com/x/passport-login/web/qrcode/generate'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}
req = urllib.request.Request(url, headers=headers)
resp = urllib.request.urlopen(req, timeout=10)
data = json.loads(resp.read().decode())

if data['code'] != 0:
    raise Exception(f"生成二维码失败: {data['message']}")

qr_url = data['data']['url']
qrcode_key = data['data']['qrcode_key']

# 保存 qrcode_key 供轮询使用
with open('/tmp/bili_qrcode_key.txt', 'w') as f:
    f.write(qrcode_key)

# 生成二维码 PNG 图片
img_path = '/home/ubuntu/Downloads/bilibili_qrcode.png'
os.makedirs(os.path.dirname(img_path), exist_ok=True)
qr = qrcode.QRCode(version=1, box_size=10, border=4)
qr.add_data(qr_url)
qr.make(fit=True)
img = qr.make_image(fill_color='black', back_color='white')
img.save(img_path)

print(f"二维码已保存: {img_path}")
print(f"qrcode_key: {qrcode_key}")
```

### Step 2: 告知用户

告知用户：
- 二维码图片路径：`/home/ubuntu/Downloads/bilibili_qrcode.png`
- 请用手机B站 App → 扫一扫 → 扫描该二维码 → 确认登录
- 二维码有效期约 3 分钟

**然后等待用户回复确认已扫码**，再执行 Step 3 轮询。

### Step 3: 轮询获取 Cookie

用户确认扫码后，执行轮询：

```python
import urllib.request, json, time, http.cookiejar

qrcode_key = open('/tmp/bili_qrcode_key.txt').read().strip()
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

url = f'https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={qrcode_key}'

for i in range(90):  # 最多等3分钟
    req = urllib.request.Request(url, headers=headers)
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read().decode())
    
    code = data['code']
    
    if code == 0 and data['data'].get('url'):
        # 登录成功，但返回的是 crossDomain URL，不是直接含 Cookie 参数
        # 需要访问该 URL，从 Set-Cookie 响应头中获取 Cookie
        cross_domain_url = data['data']['url']
        
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        # 必须用完整 UA + Referer，否则可能被风控拦截不返回 Set-Cookie
        cross_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.bilibili.com/'
        }
        cross_req = urllib.request.Request(cross_domain_url, headers=cross_headers)
        opener.open(cross_req, timeout=10)
        
        # 从 cookiejar 提取 Cookie
        cookies = {c.name: c.value for c in cj}
        sessdata = cookies.get('SESSDATA', '')
        bili_jct = cookies.get('bili_jct', '')
        dedeuserid = cookies.get('DedeUserID', '')
        
        # 关键：检查 SESSDATA 是否非空，防止"假成功"（pitfall #7）
        if not sessdata:
            print(f"警告: code=0 但 SESSDATA 为空，可能二维码已过期，需重新生成")
            break
        
        cookie = f"SESSDATA={sessdata}; bili_jct={bili_jct}; DedeUserID={dedeuserid}"
        
        # 保存到文件
        with open('/home/ubuntu/.bilibili-cookie', 'w') as f:
            f.write(cookie)
        
        print(f"登录成功! Cookie 已保存到 /home/ubuntu/.bilibili-cookie")
        break
    elif code == 86090:
        print(f"已扫码，等待确认...")
    elif code == 86101:
        print(f"等待扫码...")
    elif code == 86038:
        print(f"二维码已过期，请重新生成")
        break
    else:
        print(f"状态: code={code} msg={data['message']}")
    
    time.sleep(2)
```

### Step 4: 验证 Cookie

```python
import urllib.request, json

cookie = open('/home/ubuntu/.bilibili-cookie').read().strip()
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Cookie': cookie
}

req = urllib.request.Request('https://api.bilibili.com/x/web-interface/nav', headers=headers)
resp = urllib.request.urlopen(req, timeout=10)
data = json.loads(resp.read().decode())

if data['code'] == 0:
    d = data['data']
    print(f"验证成功: {d['uname']} (UID: {d['mid']})")
    print(f"大会员: {'是' if d.get('vipStatus') else '否'}")
else:
    print(f"验证失败: {data['code']} {data['message']}")
```

## Cookie 过期处理流程

当 Cookie 过期时（调用需登录 API 返回 code=-101，或 nav 接口返回未登录/Cookie 失效），按以下流程操作：

1. **主动告知 GK**：确认过期后明确说「Cookie 已过期，需要重新扫码登录」，不要等他问。
2. **生成新的二维码 PNG**：重新执行 Step 1，二维码图片保存到：
   `/home/ubuntu/Downloads/bilibili_qrcode.png`
3. **告知 GK 文件路径**：明确告诉他二维码图片的绝对路径，提醒他用手机 B 站 App → 扫一扫 → 下载该图片扫描，二维码有效期约 3 分钟。绝对不要在终端打印 ASCII 二维码。
4. **等待 GK 确认已扫码**后，再执行 Step 3 轮询获取新 Cookie。
5. **Step 4 验证**：确认新 Cookie 有效。

关键：过期处理的触发信号是 `-101`（未登录/Cookie 失效）。任何需要 Cookie 的操作前应先快速验证一次 nav 接口，发现过期就主动走上面流程，不要让 GK 自己发现登录失败。

## API 接口

### 生成二维码

```
GET https://passport.bilibili.com/x/passport-login/web/qrcode/generate
```

无需 Cookie。返回 `data.url`（二维码内容）和 `data.qrcode_key`（轮询用）。

### 轮询登录状态

```
GET https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={key}
```

返回 code：
- 0 = 登录成功，`data.url` 中含 Cookie 参数
- 86101 = 未扫码
- 86090 = 已扫码，等待确认
- 86038 = 二维码过期

## Cookie 存储位置

- 文件：`/home/ubuntu/.bilibili-cookie`
- 格式：`SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx`
- 同时可存储完整 Cookie 字符串（含 buvid3/buvid4 等）以应对风控

## 读取已有 Cookie

```python
cookie = open('/home/ubuntu/.bilibili-cookie').read().strip()
```

## 注意事项

- 二维码 PNG 必须保存到 `/home/ubuntu/Downloads/` 目录，用户可以下载
- **绝对不要**用 ASCII 在终端打印二维码
- Cookie 中 SESSDATA 是最核心的字段，所有需登录接口必带
- bili_jct 是 CSRF token，POST 请求必须带
- 如遇到风控（412 错误），在请求头中补充 buvid3/buvid4 等字段
- Cookie 有效期约 30 天，过期后需重新扫码
- 用户B站 UID 以 nav 接口返回为准

## WBI 签名搜索

B站搜索接口 `/x/web-interface/wbi/search/type` 需要 WBI 签名，否则返回 -403 或空结果。签名步骤：

1. 从 nav 接口获取 `wbi_img.img_url` 和 `wbi_img.sub_url`
2. 提取 URL 末尾文件名（去掉扩展名）作为 img_key / sub_key，拼接为 raw_key
3. 用固定 mixin table 对 raw_key 重排，取前 32 字符得到 mixin_key
4. 搜索参数加 `wts`（当前时间戳），按 key 排序后 urlencode
5. 拼接 mixin_key 后 MD5 得到 `w_rid`，加入参数发送请求

使用 `scripts/bili_wbi_search.py` 一键完成：

```bash
# 搜视频
python3 ~/.hermes/skills/bilibili/scripts/bili_wbi_search.py "良子 胃袋" video

# 搜用户
python3 ~/.hermes/skills/bilibili/scripts/bili_wbi_search.py "良子" bili_user
```

支持参数：`<keyword> [search_type] [page] [page_size]`，search_type 可选 video / bili_user / live_user，默认 video。

## 下载视频（yt-dlp）

yt-dlp 是下载B站视频的首选工具，带 Cookie 可解锁 1080P+。

**关键 pitfall：yt-dlp 的 `--cookies` 参数只接受 Netscape 格式文件**，不能直接传 `.bilibili-cookie`（纯字符串格式会报 `does not look like a Netscape format cookies file`）。

使用 scripts/cookie_to_netscape.py 一键转换：

```bash
python3 ~/.hermes/skills/bilibili/scripts/cookie_to_netscape.py
# 输出: /tmp/bili_netscape_cookie.txt
```

然后下载：

```bash
cd /home/ubuntu/Downloads && yt-dlp --cookies /tmp/bili_netscape_cookie.txt -o "%(title)s.%(ext)s" "https://www.bilibili.com/video/BVxxxxxxxx"
```

转换脚本读取 `/home/ubuntu/.bilibili-cookie`（字符串格式），输出 `/tmp/bili_netscape_cookie.txt`（Netscape 格式）。每次 Cookie 更新后重新跑一次即可。

## Pitfalls

1. **终端 ASCII 二维码不可靠**：终端渲染的二维码可能因字体/行距问题无法被手机识别，必须用 PNG 图片
2. **412 Precondition Failed**：yt-dlp 不带 Cookie 下载B站视频会报 412，必须带 Cookie
3. **二维码过期**：有效期约 180 秒，用户未及时扫描需重新生成
4. **轮询不能太频繁**：建议每 2 秒一次，太频繁可能被风控
5. **Cookie 过期判断**：调用 nav 接口，返回 -101 表示未登录/Cookie 过期
6. **crossDomain URL 获取 Cookie**：poll 接口返回的 `data.url` 是一个 crossDomain 跳转地址（如 `https://passport.biligame.com/x/passport-login/web/crossDomain?ticket=xxx`），不是直接包含 Cookie 参数。必须用 `http.cookiejar.CookieJar` 访问该 URL，从 Set-Cookie 响应头中提取 Cookie。直接 parse URL 的 query 参数会得到空值。
7. **poll code=0 但 Cookie 为空（假成功）**：poll 接口的外层 `code=0` 不代表登录成功——如果二维码已过期但 poll 缓存了旧状态，外层可能返回 `code=0` 但 `data.url` 为空字符串，或 `data.url` 存在但 crossDomain 跳转不带 Set-Cookie。**必须在保存 Cookie 前检查 SESSDATA 是否非空**，否则会写入 `SESSDATA=; bili_jct=; DedeUserID=` 这种空值文件，后续所有请求都会报 `-101 账号未登录`。如果发现空值，说明二维码已过期，需重新生成。
8. **yt-dlp 需要 Netscape 格式 Cookie**：`.bilibili-cookie` 是纯字符串格式（`SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx`），yt-dlp `--cookies` 参数不认，会报 `does not look like a Netscape format cookies file`。必须先转换为 Netscape 格式（用 scripts/cookie_to_netscape.py），再传给 yt-dlp。
9. **crossDomain 请求需要完整 UA + Referer**：访问 crossDomain URL 提取 Cookie 时，如果只用简短 UA 可能被风控拦截导致不返回 Set-Cookie。应使用完整 Chrome UA 并加上 `Referer: https://www.bilibili.com/`，确保 CookieJar 能拿到 SESSDATA/bili_jct/DedeUserID。
