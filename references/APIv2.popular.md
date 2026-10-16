## 热门视频流（首页"热门"tab）

> **现行可用** · 实测时间：2026-08-19

#### 调用地址

```
GET https://api.bilibili.com/x/web-interface/popular?ps={pagesize}&pn={page}
```

无需登录（公开接口）。低频分页可匿名访问。

#### 参数

| 字段 | 必选 | 类型 | 说明 |
|------|------|------|------|
| ps | false | int | 每页条数，最大 20，默认 20 |
| pn | false | int | 页码，默认 1 |

#### 返回

| 返回值字段 | 字段类型 | 字段说明 |
|------------|--------|--------|
| list | array | 视频列表 |
| no_more | bool | 是否已到最后一页 |

##### list 子项

| 返回值字段 | 字段类型 | 字段说明 |
|------------|--------|--------|
| bvid | string | BV号 |
| aid | int | AV号 |
| title | string | 视频标题 |
| desc | string | 视频简介 |
| pic | string | 封面 URL |
| tid | int | 分区号 |
| tname | string | 分区名称 |
| tidv2 | int | 新分区号 |
| tnamev2 | string | 新分区名称 |
| pubdate | int | 发布时间（UNIX Timestamp） |
| ctime | int | 创建时间（UNIX Timestamp） |
| duration | int | 视频时长（秒） |
| owner | object | UP主信息 |
| stat | object | 统计信息 |
| rcmd_reason | object | 推荐理由（可能为 null） |
| short_link_v2 | string | 短链接 |
| pub_location | string | 发布地（IP属地） |

**owner 子项**：同 [APIv2.view](./APIv2.view.md)

##### stat 子项

| 返回值字段 | 字段类型 | 字段说明 |
|------------|--------|--------|
| view | int | 播放数 |
| danmaku | int | 弹幕数 |
| reply | int | 评论数 |
| favorite | int | 收藏数 |
| coin | int | 投币数 |
| share | int | 分享数 |
| like | int | 点赞数 |

##### rcmd_reason 子项（可能为 null）

| 返回值字段 | 字段类型 | 字段说明 |
|------------|--------|--------|
| name | string | 推荐类型名 |
| content | string | 推荐理由文本 |

#### 请求示例

```python
import urllib.request, json

req = urllib.request.Request("https://api.bilibili.com/x/web-interface/popular?ps=20&pn=1")
req.add_header("User-Agent", "Mozilla/5.0 ...")
req.add_header("Referer", "https://www.bilibili.com")
resp = urllib.request.urlopen(req, timeout=10)
data = json.loads(resp.read().decode())

for v in data["data"]["list"]:
    stat = v["stat"]
    print(f"[{v['bvid']}] {v['title']}  播放:{stat['view']}  分区:{v.get('tname')}  UP:{v['owner']['name']}")
```

#### 备注

- 最多可翻 ~5 页（100条），`no_more=true` 后停止
- 各页间建议间隔 ≥1 秒，避免触发 -799 风控
