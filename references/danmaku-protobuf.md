# B站弹幕爬取（Protobuf 接口）

## 接口

```
GET https://api.bilibili.com/x/v2/dm/web/seg.so?type=1&oid={cid}&segment_index={n}
```

- `type=1` = 弹幕（type=2 = 字幕）
- `oid` = 视频的 cid（从 `view` 接口获取，非 bvid）
- `segment_index` 从 1 开始，每段约 6 分钟视频。拉 6 段基本覆盖大部分视频。
- 需要 Cookie + Referer 头，否则可能被风控。

## 获取 cid

```python
url = f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}'
# data['data']['cid'] 即为弹幕 oid
# 多P视频: data['data']['pages'][i]['cid'] 每个P有独立cid
```

## Protobuf 手动解析（无需 .proto 文件）

响应是二进制 protobuf，无需安装 protobuf 库，手动解析即可：

```python
def read_varint(data, pos):
    """读取 varint 编码的整数"""
    result = 0
    shift = 0
    while pos < len(data):
        b = data[pos]
        result |= (b & 0x7F) << shift
        pos += 1
        if not (b & 0x80):
            break
        shift += 7
    return result, pos

def parse_message(data):
    """解析 protobuf message，返回 [(field_number, wire_type, value)]"""
    fields = []
    pos = 0
    while pos < len(data):
        tag, pos = read_varint(data, pos)
        field_number = tag >> 3
        wire_type = tag & 0x07
        if wire_type == 0:    # Varint
            value, pos = read_varint(data, pos)
        elif wire_type == 2:  # Length-delimited (string/bytes/embedded)
            length, pos = read_varint(data, pos)
            value = data[pos:pos+length]
            pos += length
        elif wire_type == 5:  # 32-bit
            value = data[pos:pos+4]; pos += 4
        elif wire_type == 1:  # 64-bit
            value = data[pos:pos+8]; pos += 8
        else:
            break
        fields.append((field_number, wire_type, value))
    return fields
```

## DanmakuElem 字段映射

顶层 `DmSegMobileReply` 只有一个字段 `1`（repeated DanmakuElem），wire_type=2。

每条 DanmakuElem 的关键字段：

| field | 类型 | 含义 |
|-------|------|------|
| 1 | varint | 弹幕 id |
| 2 | varint | progress（出现时间，毫秒） |
| 3 | varint | mode（1=滚动 4=底部 5=顶部 6=逆向 7=高级 8=代码 9=BAS） |
| 4 | varint | 字号 |
| 5 | varint | 颜色（RGB int） |
| 6 | string | 发送者 midHash |
| 7 | string | **弹幕内容** |
| 8 | varint | ctime（发送时间戳） |

## 完整采集流程

```python
# 1. 从 view 接口拿 cid
# 2. 循环拉 segment_index=1..6
# 3. 对每段，parse_message 拿到 field 1 的列表
# 4. 对每个 field 1 的 value 再 parse_message，提取 field 2/3/7
# 5. 按 progress 排序，输出 txt
```

## 输出格式示例

```
[00:00.000] [滚动] 惊了
[00:03.000] [滚动] 惊了
[00:07.000] [滚动] 我运行如天堂
```

时间格式 `MM:SS.mmm`，方括号内为弹幕类型。

## 数据量参考

- 普通视频：1-3 个 segment，500-1200 条弹幕
- 热门视频：可能需要更多 segment
- 每段约 100-600 条弹幕，取决于视频热度和时长

## Pitfalls

1. **XML 接口已废弃**：`comment.bilibili.com/{cid}.xml` 返回的不是有效 XML（可能是压缩或重定向），protobuf 接口才是当前可用方案。
2. **wire_type=2 的 value 是 bytes**：需要 `.decode('utf-8')` 转字符串，field 7（content）必须转。
3. **空 segment 两种形态**（2026-10实测）：视频时长不够时，后续 segment_index 要么返回空数据（<10 bytes），要么返回 **HTTP 304 Not Modified**（urllib 直接抛 HTTPError）。两种都要 try/except 跳过，304 不代表失败。
