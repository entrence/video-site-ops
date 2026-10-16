# B站评论 API 参考

## 1. BVID -> AID 转换

```
GET https://api.bilibili.com/x/web-interface/view?bvid={BVID}
```

带 Cookie。返回 `data.aid` (avid), `data.cid`, `data.title`, `data.owner.name`。
此接口一直稳定，从未被风控。

## 2. 拉取评论列表

```
GET https://api.bilibili.com/x/v2/reply/main?type=1&oid={AID}&mode={mode}&next={cursor}&ps={pagesize}
```

参数:
| 字段 | 必选 | 说明 |
|------|------|------|
| type | 是 | 1=视频, 12=专栏, 11=动态 |
| oid | 是 | avid |
| mode | 否 | 3=按热度, 2=按时间 |
| next | 否 | 翻页 cursor, 首页=0 |
| ps | 否 | 每页条数, 默认30 |

返回 `data.replies[]`, 每条:
- `rpid` — 评论ID
- `member.uname` / `member.mid` — 评论者
- `content.message` — 评论内容
- `like` — 点赞数
- `count` — 子回复数
- `replies[]` — 前3条子回复

注意: 新视频可能评论很少（只有几条），这是正常的，不是接口问题。

## 3. 发表评论

```
POST https://api.bilibili.com/x/v2/reply/add
Content-Type: application/x-www-form-urlencoded
Cookie: SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx
Referer: https://www.bilibili.com/video/{BVID}
Origin: https://www.bilibili.com
```

参数（form-urlencoded）:
| 字段 | 必选 | 说明 |
|------|------|------|
| oid | 是 | avid |
| type | 是 | 1=视频 |
| message | 是 | 评论内容 (1-1000字符) |
| platf | 是 | 平台标志, 固定1 |
| root | 否 | 根评论rpid, 一级评论=0 |
| parent | 否 | 父评论rpid, 一级评论=0, 回复时=root或具体父rpid |
| csrf | 是 | = bili_jct 的值 |

成功返回 `data.rpid`, `data.reply.content.message`。

错误码:
| code | 含义 |
|------|------|
| 0 | 成功 |
| -101 | 账号未登录, Cookie过期 |
| -403 | 权限不足 |
| -509 | 请求过于频繁 |
| -635 | 该视频不允许发布评论 |
| -636 | 发送的数据不合法 |
| -637 | 系统禁止的信息（含敏感词） |
| 12015 | 内容长度超限 |

## 4. 删除评论

```
POST https://api.bilibili.com/x/v2/reply/del
Content-Type: application/x-www-form-urlencoded
Cookie: SESSDATA=xxx; bili_jct=xxx
Referer: https://www.bilibili.com/video/{BVID}
Origin: https://www.bilibili.com
```

参数:
| 字段 | 必选 | 说明 |
|------|------|------|
| oid | 是 | avid |
| type | 是 | 1=视频 |
| rpid | 是 | 要删除的评论rpid |
| csrf | 是 | = bili_jct 的值 |

返回 `code=0, message=OK` 即成功。只能删自己发的评论。测试后清理用。

## 5. 回复关系说明

B站评论有两层结构:
- **一级评论**: root=0, parent=0。直接挂在视频下。
- **二级回复**: root=被回复的一级评论rpid, parent=被回复的评论rpid。
  - 回复一级评论: root=该评论rpid, parent=该评论rpid
  - 回复二级评论: root=一级评论rpid, parent=被回复的二级评论rpid

所有回复都挂在一级评论下, 通过 root 指向。

## 6. 请求头要求

所有 POST 请求必须带:
- `Cookie`: 含 SESSDATA + bili_jct + DedeUserID
- `Referer`: https://www.bilibili.com/video/{BVID}
- `Origin`: https://www.bilibili.com
- `User-Agent`: 完整 Chrome UA 字符串
- `Content-Type`: application/x-www-form-urlencoded

GET 请求带 Cookie + User-Agent 即可。

## 7. 搜索接口（查找用户/视频）

### 接口可靠性总览

| 接口 | 路径 | 状态 | 说明 |
|------|------|------|------|
| 视频搜索 | `/x/web-interface/wbi/search/type?search_type=video` | 可用 | 按用户名搜视频，order=pubdate 取最新 |
| 用户搜索 | `/x/web-interface/wbi/search/type?search_type=bili_user` | 可用 | 找用户 mid |
| BVID→AID | `/x/web-interface/view?bvid=<BVID>` | 可用 | 一直稳定 |
| 评论列表 | `/x/v2/reply/main` | 可用 | mode=3热度/2时间 |
| 删除评论 | `/x/v2/reply/del` | 可用 | POST |
| 空间视频列表(旧) | `/x/space/arc/search?mid=<MID>` | -799 限流 | 服务器 IP 被限流，重试无效 |
| 空间视频列表(wbi) | `/x/space/wbi/arc/search?mid=<MID>` | -403 | 需 wbi 签名（w_rid 等），实现复杂 |
| 搜索(非wbi) | `/x/web-interface/search/type` | 风控 | 返回 HTML 错误页，必须用 wbi 路径 |

### 搜索用户

```
GET https://api.bilibili.com/x/web-interface/wbi/search/type?search_type=bili_user&keyword=<URL编码的用户名>&page=1&page_size=20
```

带 Cookie + User-Agent + `Referer: https://search.bilibili.com/`。
返回 `data.result[]`, 每条含 `mid`, `uname`, `usign`(签名), `fans`, `videos`。

### 搜索视频（查找用户最新视频）

```
GET https://api.bilibili.com/x/web-interface/wbi/search/type?search_type=video&keyword=<URL编码的关键词>&order=pubdate&page=1&page_size=5
```

参数:
| 字段 | 必选 | 说明 |
|------|------|------|
| search_type | 是 | 固定 video |
| keyword | 是 | URL编码的搜索词，可传用户名 |
| order | 否 | pubdate=按发布时间(最新), click=按播放量, scores=按评论数 |
| page | 否 | 页码 |
| page_size | 否 | 每页条数 |

返回 `data.result[]`, 每条含 `bvid`, `aid`, `title`(含em标签需清洗), `author`, `pubdate`。
title 字段含 `<em class="keyword">` 高亮标签，用 `re.sub('<[^>]+>', '', title)` 清洗。
order=pubdate 按发布时间排序，取第一条即为最新视频。

### 为什么不用空间视频列表接口

- `/x/space/arc/search` 从服务器 IP 调用返回 -799 限流，等几秒重试也无效
- `/x/space/wbi/arc/search` 需要 wbi 签名（计算 w_rid + wtv + 其他参数），实现复杂
- 搜索接口 (`wbi/search/type`) 不需要 wbi 签名，用用户名做关键词即可搜到视频列表，是获取用户最新视频的最简方案
