---
name: bilibili-video-download
description: Download Bilibili videos via API when yt-dlp fails with 412 Precondition Failed
trigger: yt-dlp fails on bilibili.com URL with HTTP 412, need alternative download method
---

# Bilibili Video Download (API Method)

## When to use
- yt-dlp fails with `HTTP Error 412: Precondition Failed` on bilibili.com URLs
- Need to download a Bilibili video for the user

## Steps

### 1. Resolve short URL
```bash
curl -sL -o /dev/null -w '%{url_effective}' 'https://b23.tv/XXXXX'
```
Extract BV ID (format: `BVXXXXXXXXXX`) from the resolved URL.

### 2. Get video metadata (CID)
```python
import requests
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.bilibili.com'
})
resp = session.get(f"https://api.bilibili.com/x/web-interface/view?bvid={BVID}")
data = resp.json()
CID = data['data']['cid']
title = data['data']['title']
```

### 3. Get playable URL (CRITICAL: use platform=html5)
The key trick: add `platform=html5` to get `durl` format (direct mp4) instead of `dash` format (separate video/audio streams that return 403).

```python
url = f"https://api.bilibili.com/x/player/playurl?bvid={BVID}&cid={CID}&qn=16&fnval=0&platform=html5&high_quality=1"
resp = session.get(url, timeout=15)
data = resp.json()
video_url = data['data']['durl'][0]['url']  # Direct mp4 URL
```

- `qn=16` = 360p (lowest, most compatible). Use `qn=32` for 480p, `qn=64` for 720p, `qn=80` for 1080p.
- `fnval=0` = durl format (NOT dash). dash URLs return 403 from CDN without proper cookies.
- `platform=html5` = forces durl response instead of dash.

### 4. Download the video
```python
v_resp = session.get(video_url, timeout=60, headers={'Referer': 'https://www.bilibili.com'})
with open('output.mp4', 'wb') as f:
    f.write(v_resp.content)
```

The `Referer: https://www.bilibili.com` header is REQUIRED or CDN returns 403.

### 5. Transcode for WeChat (optional)
```bash
ffmpeg -i input.mp4 -c:v libx264 -preset fast -crf 28 -c:a aac -b:a 128k -movflags +faststart output_weixin.mp4 -y
```

## Pitfalls
- **412 error**: yt-dlp gets blocked by Bilibili's anti-bot. Use the API method above.
- **403 on dash URLs**: `fnval=4048` (dash format) returns separate video/audio URLs that 403 without session cookies. Always use `fnval=0&platform=html5` to get durl (single mp4).
- **Missing Referer**: CDN requires `Referer: https://www.bilibili.com` header or returns 403.
- **qn limits without login**: Without login cookies, max quality may be limited to 360p/480p.
