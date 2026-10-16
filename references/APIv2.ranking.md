## 全站/分区排行榜

> **现行可用** · 实测时间：2026-08-19

#### 调用地址

```
GET https://api.bilibili.com/x/web-interface/ranking/v2?rid={rid}&type={type}
```

无需登录（公开接口）。

#### 参数

| 字段 | 必选 | 类型 | 说明 |
|------|------|------|------|
| rid | true | int | 分区号，0=全站，其他=具体分区（如 1=动画、4=游戏、5=娱乐、36=科技、160=生活、211=美食、223=音乐、234=体育等） |
| type | false | string | 排行类型：all=全部稿件（默认），origin=仅原创稿件 |

#### 返回

| 返回值字段 | 字段类型 | 字段说明 |
|------------|--------|--------|
| note | string | 榜单说明文本 |
| list | array | 视频列表（全站最多100条，分区最多~100条） |

##### list 子项

字段与 [popular](./APIv2.popular.md) 基本相同，额外包含：

| 返回值字段 | 字段类型 | 字段说明 |
|------------|--------|--------|
| score | int | 榜单得分（综合评分，用于排序） |

其余字段（bvid, aid, title, tid, tname, pubdate, owner, stat 等）同 popular。

##### stat 子项

同 [APIv2.popular](./APIv2.popular.md)。

#### 请求示例

```python
import urllib.request, json

# 全站排行
req = urllib.request.Request("https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all")
req.add_header("User-Agent", "Mozilla/5.0 ...")
req.add_header("Referer", "https://www.bilibili.com")
resp = urllib.request.urlopen(req, timeout=10)
data = json.loads(resp.read().decode())

print(data["data"]["note"])  # 榜单说明
for v in data["data"]["list"][:10]:
    stat = v["stat"]
    print(f"[{v['bvid']}] {v['title']}  播放:{stat['view']}  分区:{v.get('tname')}  UP:{v['owner']['name']}")
```

#### 备注

- 全站榜(rid=0)返回100条，分区榜返回~100条
- 常用分区 rid：0=全站, 1=动画, 4=游戏, 5=娱乐, 36=科技, 119=鬼畜, 160=生活, 211=美食, 223=音乐, 234=体育, 188=科普
- `type=origin` 过滤掉转载稿件，只保留原创
