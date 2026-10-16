---
name: bilibili-daily-report
version: 1.0.0
author: entrence
description: B站日报生成器。拉取B站热门视频+全站排行榜数据，统计分区热度/综合热度/播放量/互动率，生成精美PPT日报。
---

# B站日报生成器

## 触发条件

- 用户要求生成B站日报/周报/热点报表
- 用户要求定时汇报B站视频热度数据
- 用户要求分析B站哪个分区/视频最火

## 概述

从B站API拉取今日热门视频数据，统计分区热度分布、综合热度排行、播放量排行、互动率排行，生成5页精美PPT日报。全程无需Cookie（使用公开接口），耗时约15秒。

## 数据源（无需Cookie）

两个B站公开接口，合并去重后约150-180条样本：

1. **热门视频流** `GET https://api.bilibili.com/x/web-interface/popular?ps=20&pn={page}`
   - 首页"热门"tab数据，可翻5页=100条
   - 返回：bvid, title, tid, tname(分区名), stat(view/like/coin/favorite/reply/share), owner, rcmd_reason
   - 详见 `references/APIv2.popular.md`

2. **全站排行榜** `GET https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all`
   - 全站综合榜，100条
   - 返回字段同popular，额外有score(榜单得分)
   - 分区榜改rid参数：1=动画, 4=游戏, 5=娱乐, 36=科技, 160=生活, 211=美食, 223=音乐
   - 详见 `references/APIv2.ranking.md`

## 统计指标

| 指标 | 算法 | 用途 |
|------|------|------|
| 分区上榜数 | 按tname分组计数 | 哪个分区今天产出最多热门 |
| 分区累计播放 | 按tname分组求和view | 哪个分区今天流量最大 |
| 综合热度 | view + like×5 + coin×10 + favorite×3 + share×8 + reply×3 | 加权排行，体现深度互动 |
| 互动率 | (like+coin+favorite+reply+share) / view | 越高说明观众参与度越强 |

## 一键生成

```bash
bash /home/ubuntu/.hermes/skills/bilibili/scripts/run_daily.sh
```

输出：`/home/ubuntu/bilibili-daily/B站日报_YYYY-MM-DD.pptx`

## 分步执行

### Step 1: 拉取数据

```bash
python3 /home/ubuntu/.hermes/skills/bilibili/scripts/fetch_data.py
# 输出: /home/ubuntu/bilibili-daily/data.json
```

### Step 2: 生成PPT

```bash
export NODE_PATH=/home/ubuntu/.npm-global/lib/node_modules
node /home/ubuntu/.hermes/skills/bilibili/scripts/gen_pptx.js
# 输出: /home/ubuntu/bilibili-daily/B站日报_YYYY-MM-DD.pptx
```

### Step 3: 视觉QA（可选）

```bash
cd /home/ubuntu/bilibili-daily
soffice --headless --convert-to pdf "B站日报_YYYY-MM-DD.pptx"
pdftoppm -jpeg -r 150 "B站日报_YYYY-MM-DD.pdf" slide
# 逐页检查 slide-*.jpg
```

用 delegate_task 分配 subagent 做视觉QA更佳（fresh eyes）。

## PPT设计规格

- **布局**: LAYOUT_16x9 (10"×5.625")
- **配色**: Coral Energy（深蓝灰1E293B背景 + 珊瑚红E64A4A + 金色FBBF24 + 粉色FB7185 + 青绿0D9488）
- **字体**: Arial Black(标题) + Calibri(正文)
- **图标**: react-icons (FaFire/FaPlay/FaHeart/FaChartBar/FaTv/FaStar) 经sharp转PNG

### 5页结构

1. **封面** - 标题+日期+采样统计+装饰圆
2. **分区热度排行** - 左水平柱状图(上榜数TOP8) + 右累计播放TOP5卡片
3. **综合热度TOP5** - 深色卡片列表，第1名金色高亮，含六维数据
4. **播放量&互动率** - 左播放量TOP5卡片 + 右高互动率TOP3大百分比
5. **数据总览** - 4个大数字统计卡 + 今日洞察4条

## 前置依赖

```bash
# Node.js (pptxgenjs + react-icons + sharp)
npm install -g pptxgenjs react-icons react react-dom sharp

# Python (标准库，无需额外安装)
# 系统工具
sudo apt install -y libreoffice poppler-utils  # PDF转换+图片渲染
```

## 定时任务配置

可用 cronjob 设置每日自动生成：

```
cronjob action=create
schedule=0 9 * * *    # 每天早上9点
prompt=执行B站日报生成：bash /home/ubuntu/.hermes/skills/bilibili/scripts/run_daily.sh，完成后告知PPT文件路径
skills=["bilibili-daily-report"]
```

注意：CLI环境下cronjob输出不自动推送到终端。如需推送，deliver参数需指向已连接的消息平台（如telegram）。

## 输出文件

| 文件 | 说明 |
|------|------|
| `/home/ubuntu/bilibili-daily/data.json` | 结构化数据快照 |
| `/home/ubuntu/bilibili-daily/B站日报_YYYY-MM-DD.pptx` | PPT日报 |
| `/home/ubuntu/bilibili-daily/YYYY-MM-DD.txt` | 纯文本日报（备用） |

## 文件结构

```
/home/ubuntu/bilibili-daily/
├── fetch_data.py      # 数据拉取脚本
├── gen_pptx.js        # PPT生成脚本
├── run_daily.sh       # 一键调度脚本
├── data.json          # 当前数据快照
└── B站日报_*.pptx     # 历史日报
```

## 弹幕爬取

除日报外，本 skill 也支持爬取单个视频弹幕为 txt。B站弹幕走 protobuf 接口（`seg.so`），需手动解析无 .proto 文件。详见 `references/danmaku-protobuf.md`。

## API文档

详细的B站API文档位于 `/home/ubuntu/bilibili-api-docs/`，本skill相关接口：
- `APIv2.popular.md` - 热门视频流
- `APIv2.ranking.md` - 全站/分区排行榜
- `APIv2.view.md` - 视频详情
- `CONST.cookie.md` - Cookie字段说明
- `references/danmaku-protobuf.md` - 弹幕 protobuf 爬取

## Pitfalls

1. **-799风控**：popular和ranking接口虽然无需Cookie，但分页请求过快会触发-799。每页间隔≥1秒。
2. **no_more截断**：popular接口不一定能翻满5页，`no_more=true`后要停止，实际可能只有80-100条。
3. **分区名缺失**：极少数视频tname为null，统计时需fallback为"未知"。
4. **热门流≠排行榜**：两个数据源有部分重叠但不完全相同，合并去重后样本更全面。popular偏实时推荐，ranking偏综合排名。
5. **pptxgenjs选项对象不可复用**：shadow等option对象会被原地修改（转为EMU），多次addShape必须每次创建新对象，否则第二次调用会损坏文件。
6. **hex颜色不加#**：pptxgenjs的color参数用"FF0000"而非"#FF0000"，带#会导致文件损坏。
7. **LibreOffice渲染图表差异**：pptxgenjs生成的图表用Microsoft PowerPoint打开效果最佳，LibreOffice/soffice转PDF时图表样式可能有细微差异（颜色、字体渲染），但不影响数据正确性。
