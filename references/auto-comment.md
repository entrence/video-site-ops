---
name: bilibili-auto-comment
version: 1.0.0
author: entrence
description: B站自动评论机器人。持续获取B站最新发布的视频，在每个视频下评论"行"，去重防重复，记录到Excel。
---

# B站自动评论机器人

## 触发条件

用户要求自动在B站最新视频下批量评论，持续运行。

典型场景:
- "去找b站最新发布的视频，每个视频下评论'行'"
- "自动评论100个视频，sleep 5分钟，再继续"

## 依赖

- Cookie 文件 `~/.bilibili-cookie`（由 `bilibili-cookie` skill 产出）
- Python 包: `openpyxl`（写Excel）
- 关联 skill: references/comment-api.md（评论API参考）、references/cookie-login.md（Cookie管理）

## 快速用法

```bash
# 前台测试（跑一轮，评论5个）
python3 ~/.hermes/skills/bilibili/scripts/bili_auto_comment.py --once --count 5

# 正式运行（每轮30个，间隔10分钟，无限循环）
# ⚠️ count=100+interval=300 会导致B站12014限流，不要用
python3 ~/.hermes/skills/bilibili/scripts/bili_auto_comment.py --count 30 --interval 600

# 后台运行（Hermes环境中）
# 方式1: terminal(background=true, notify_on_complete=true) — 进程管理器跟踪，日志在 process session
# 方式2: subprocess.Popen(stdout=log, start_new_session=True) — 日志写到文件，可 tail -f
# 不要用 nohup/disown/setsid（foreground terminal会报错拒绝）

# 停止
kill <PID>  # 或用 process(action='kill')
```

## 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--count` | 100 | 每轮评论视频数量 |
| `--interval` | 300 | 每轮间隔秒数（5分钟=300） |
| `--once` | False | 只跑一轮就退出（测试用） |
| `--message` | 行 | 评论内容 |
| `--excel` | ~/Downloads/bili_auto_comment.xlsx | Excel记录文件路径 |
| `--keyword` | 的 | 搜索关键词（用"的"可命中最多最新视频） |

## 工作流程

1. 读取Cookie，解析SESSDATA/bili_jct/DedeUserID
2. 加载已评论Excel，构建已评论BVID集合（去重）
3. 搜索B站最新视频（order=pubdate），翻页直到收集足够新视频
4. 逐个评论：BVID→AID→POST reply/add
5. 每条评论结果写入Excel（时间/BVID/AID/标题/作者/状态/rpid）
6. 间隔指定秒数后重复
7. 已评论的BVID不会重复评论

## Excel 记录格式

| 时间 | BVID | AID | 视频标题 | 作者 | 评论内容 | 状态 | rpid | 错误信息 |
|------|------|-----|----------|------|----------|------|------|----------|

## 去重机制

- 启动时读取Excel所有已记录的BVID，存入set
- 搜索阶段用 `seen` set 跟踪当前批次已收集的BVID（初始化为历史已评论集合的副本）
- 每收集一个新BVID就加入 `seen`，翻页时碰到已存在的直接跳过
- 评论成功后立即加入set并写入Excel

## 标题过滤

- 带"第x集"的视频（如"第一集"、"第1集"、"第12集"等）自动跳过不评论
- 正则匹配: `re.search(r"第.{1,4}集", title)`
- 可在脚本 `search_latest_videos` 函数中修改过滤规则

## 风控处理

- `-509` 请求过于频繁: 等待10秒后重试，最多3次
- `-101` 账号未登录: Cookie过期，打印警告并退出（需重新登录）
- `-635` 视频不允许评论: 跳过该视频
- `-637` 敏感词: 跳过
- `12014` 发送失败，已达到当前评论发送上限: 当天评论数达到B站限额（约200-300条），所有后续评论都会失败。脚本目前直接记录失败并继续下一个视频（不暂停不重试）。**大面积出现12014时应立即停止脚本**，等次日限额重置后再跑。预防: 每轮count≤30，interval≥600秒
  - **限流恢复周期是24小时，不是几小时**: 实测被限流后等3小时仍未解除，需要等到次日。不要短间隔重试验证是否恢复
- `12045` 购买后即可发表评论: 付费视频，跳过
- `12061` UP主已关闭评论区: 跳过
- 每条评论间隔1-3秒随机延迟，避免触发风控

## 注意事项

1. **搜索关键词**: 默认用"的"搜索，因为这是中文最高频字，能命中最多最新视频。可改`--keyword`参数
2. **翻页**: 每页20条，需要count/20页才能收集足够视频。实际会多取一些过滤已评论的
3. **Excel并发安全**: 单进程运行，不涉及并发写入
4. **Cookie过期**: 脚本检测到-101会退出，需重新用bilibili-cookie skill登录后重启
5. **长时间运行**: 推荐 `terminal(background=true, notify_on_complete=true)` 或 `subprocess.Popen(start_new_session=True)` 后台运行
6. **日志实时刷新**: 脚本已内置 `functools.partial(print, flush=True)` 全局 autoflush，重定向到文件时日志实时写入。如移除该行，需用 `python3 -u` 或 `PYTHONUNBUFFERED=1` 启动

## Pitfalls

1. **搜索接口不需要wbi签名**: 用`/x/web-interface/wbi/search/type`路径即可，不是`/x/space/arc/search`（那个会被-799限流）
2. **oid是avid不是bvid**: POST评论时oid必须传avid，需先view接口转换
3. **csrf=bili_jct**: POST必须带csrf参数，值等于bili_jct
4. **每条评论要随机延迟**: 固定间隔容易被风控识别，用1-3秒随机延迟
5. **Excel文件被占用**: 如果用户在Excel中打开了文件，写入会失败。脚本会重试3次
6. **搜索结果可能不够**: 新视频每分钟都在增加，但搜索结果有延迟。count=100时可能需要翻5-10页
7. **评论发送上限(code=12014)**: B站评论有24小时发送上限，触发后需等24小时才能恢复。count=100太容易触发，建议count=30+interval=600(10分钟)。恢复周期是24小时不是几小时——实测等3小时仍未解除
8. **搜索翻页重叠导致重复评论**: B站搜索相邻页结果有重叠，仅用历史已评论set去重不够，必须用 `seen` set 跟踪当前批次已收集的BVID（已修复）
9. **"第x集"过滤**: 标题匹配`第.{1,4}集`的视频(如"第一集"、"第38集")会被跳过不评论
10. **后台运行方式**: Hermes foreground terminal 会拒绝 nohup/disown/setsid 等 shell-level background wrappers。用 `terminal(background=true)` 或 `subprocess.Popen(start_new_session=True)` 替代
11. **日志不刷新**: Python stdout 重定向到文件时默认全缓冲，日志不会实时写入。脚本已内置 `functools.partial(print, flush=True)` 全局 autoflush 解决此问题。如果移除该行，须用 `python3 -u` 或设 `PYTHONUNBUFFERED=1`
12. **启动前先检查残留进程**: 启动新实例前必须 `ps aux | grep bili_auto_comment | grep -v grep` 检查是否有旧进程残留。多进程同时运行会导致重复评论、争夺Excel写入权限、加速触发12014限流
13. **12014限流恢复周期是24小时**: 实测被限流后等3小时仍未解除，需要等到次日。不要通过短间隔重启来"试"是否恢复——每次启动都搜索+请求会加重风控。用 crontab 定时任务到次日重启即可
14. **定时重启用 crontab 不要用 sleep**: `sleep 10800` 后台进程容易被系统回收。用 `crontab -e` 设定一次性定时任务更可靠（如 `0 8 28 8 * python3 ...`），任务执行后手动清除 crontab 条目

## 关联 Skill

- `bilibili-cookie`: Cookie获取与刷新
- `bilibili-comment`: 评论API详细参考
