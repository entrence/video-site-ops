#!/usr/bin/env python3
"""
B站自动评论机器人
持续获取B站最新发布的视频，在每个视频下评论指定内容，去重防重复，记录到Excel。

用法:
  # 前台测试（跑一轮，评论5个）
  python3 bili_auto_comment.py --once --count 5

  # 正式运行（每轮30个，间隔10分钟，无限循环）
  # ⚠️ count=100+interval=300 会导致B站12014限流，不要用
  python3 bili_auto_comment.py --count 30 --interval 600

  # 后台运行（Hermes环境）
  # 方式1: terminal(background=true, notify_on_complete=true)
  # 方式2: subprocess.Popen(stdout=log, start_new_session=True) — 日志写到文件，可 tail -f
  # 不要用 nohup/disown/setsid（Hermes foreground terminal会报错拒绝）
"""

import argparse
import json
import os
import random
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime

# stdout 实时刷新（重定向到文件时不缓冲）
import functools
print = functools.partial(print, flush=True)

# Excel 依赖
try:
    from openpyxl import Workbook, load_workbook
except ImportError:
    print("[FATAL] 缺少 openpyxl，请运行: pip3 install openpyxl --break-system-packages")
    sys.exit(1)

# ============== 常量 ==============

COOKIE_FILE = os.path.expanduser("~/.bilibili-cookie")
DEFAULT_EXCEL = os.path.expanduser("~/Downloads/bili_auto_comment.xlsx")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

SEARCH_URL = "https://api.bilibili.com/x/web-interface/wbi/search/type"
VIEW_URL = "https://api.bilibili.com/x/web-interface/view"
REPLY_ADD_URL = "https://api.bilibili.com/x/v2/reply/add"

EXCEL_HEADERS = ["时间", "BVID", "AID", "视频标题", "作者", "评论内容", "状态", "rpid", "错误信息"]


# ============== Cookie ==============

def load_cookie():
    """读取 ~/.bilibili-cookie，返回 dict {SESSDATA, bili_jct, DedeUserID} 和 cookie字符串"""
    if not os.path.exists(COOKIE_FILE):
        print(f"[FATAL] Cookie 文件不存在: {COOKIE_FILE}")
        print("请先用 bilibili-cookie skill 二维码登录获取 Cookie")
        sys.exit(1)

    raw = open(COOKIE_FILE).read().strip()
    # 去除可能的 "1|" 前缀
    if "|" in raw:
        raw = raw.split("|", 1)[1]

    pairs = {}
    for part in raw.split("; "):
        if "=" in part:
            k, v = part.split("=", 1)
            pairs[k.strip()] = v.strip()

    if "SESSDATA" not in pairs or not pairs["SESSDATA"]:
        print("[FATAL] Cookie 中 SESSDATA 为空，可能已过期")
        print("请用 bilibili-cookie skill 重新扫码登录")
        sys.exit(1)

    cookie_str = f"SESSDATA={pairs['SESSDATA']}; bili_jct={pairs.get('bili_jct','')}; DedeUserID={pairs.get('DedeUserID','')}"
    return pairs, cookie_str


# ============== HTTP ==============

def http_get(url, cookie_str, referer=None, timeout=15):
    """GET 请求，返回 JSON dict"""
    headers = {
        "User-Agent": UA,
        "Cookie": cookie_str,
    }
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read().decode("utf-8"))


def http_post(url, cookie_str, data, referer=None, timeout=15):
    """POST 请求 (form-urlencoded)，返回 JSON dict"""
    headers = {
        "User-Agent": UA,
        "Cookie": cookie_str,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    if referer:
        headers["Referer"] = referer
        headers["Origin"] = "https://www.bilibili.com"
    post_data = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=post_data, headers=headers)
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read().decode("utf-8"))


# ============== 搜索最新视频 ==============

def search_latest_videos(cookie_str, keyword, needed, existing_bvids):
    """
    搜索B站最新视频，翻页直到收集到 needed 个未评论的视频。
    返回 list of dict: {bvid, aid, title, author, pubdate}
    """
    collected = []
    seen = set(existing_bvids)  # 当前批次已收集的BVID（含历史），防止翻页重叠导致重复
    page = 1
    max_pages = (needed // 20) + 5  # 多翻几页以防过滤已评论的

    while len(collected) < needed and page <= max_pages:
        kw_encoded = urllib.parse.quote(keyword)
        url = (
            f"{SEARCH_URL}?search_type=video"
            f"&keyword={kw_encoded}"
            f"&order=pubdate"
            f"&page={page}"
            f"&page_size=20"
        )
        try:
            data = http_get(url, cookie_str, referer="https://search.bilibili.com/")
        except Exception as e:
            print(f"  [WARN] 搜索第{page}页失败: {e}")
            page += 1
            time.sleep(2)
            continue

        if data.get("code") != 0:
            print(f"  [WARN] 搜索返回 code={data.get('code')} message={data.get('message')}")
            # -509 限流，等待后重试
            if data.get("code") == -509:
                print("  搜索被限流，等待15秒...")
                time.sleep(15)
                continue
            break

        results = data.get("data", {}).get("result", [])
        if not results:
            print(f"  第{page}页无结果，停止翻页")
            break

        for v in results:
            bvid = v.get("bvid", "")
            if not bvid:
                continue
            if bvid in seen:
                continue  # 已评论过或当前批次已收集，跳过
            title = re.sub("<[^>]+>", "", v.get("title", ""))
            # 跳过带"第x集"的视频（如"第一集"、"第1集"、"第10集"等）
            if re.search(r"第.{1,4}集", title):
                print(f"    [SKIP] 标题含'第x集'，跳过: {title[:40]}")
                continue
            seen.add(bvid)
            collected.append({
                "bvid": bvid,
                "aid": str(v.get("aid", "")),
                "title": title,
                "author": v.get("author", ""),
                "pubdate": v.get("pubdate", 0),
            })
            if len(collected) >= needed:
                break

        print(f"  第{page}页获取{len(results)}条，累计收集{len(collected)}条新视频")
        page += 1
        time.sleep(1)  # 翻页间隔

    return collected


# ============== 发评论 ==============

def post_comment(cookie_str, pairs, bvid, aid, message, max_retries=3):
    """
    在视频下发评论。
    返回 (success: bool, rpid: str, error_msg: str)
    """
    for attempt in range(max_retries):
        try:
            data = http_post(
                REPLY_ADD_URL,
                cookie_str,
                {
                    "oid": aid,
                    "type": "1",
                    "message": message,
                    "platf": "1",
                    "root": "0",
                    "parent": "0",
                    "csrf": pairs.get("bili_jct", ""),
                },
                referer=f"https://www.bilibili.com/video/{bvid}",
            )
        except Exception as e:
            return False, "", f"请求异常: {e}"

        code = data.get("code", -999)
        msg = data.get("message", "")

        if code == 0:
            rpid = str(data.get("data", {}).get("rpid", ""))
            return True, rpid, ""

        # 错误处理
        if code == -509:
            # 请求过于频繁，等待后重试
            wait = 10 * (attempt + 1)
            print(f"    -509 限流，等待{wait}秒后重试 ({attempt+1}/{max_retries})")
            time.sleep(wait)
            continue
        elif code == -101:
            # Cookie过期，不可重试
            return False, "", f"Cookie过期(code=-101)，请重新登录"
        elif code == -635:
            return False, "", "视频不允许评论"
        elif code == -637:
            return False, "", "含敏感词"
        elif code == -636:
            return False, "", "数据不合法"
        elif code == 12015:
            return False, "", "内容长度超限"
        else:
            return False, "", f"code={code} message={msg}"

    return False, "", "重试次数用尽"


# ============== Excel 记录 ==============

def init_excel(excel_path):
    """初始化Excel文件，如果不存在则创建并写表头"""
    if os.path.exists(excel_path):
        return load_workbook(excel_path)
    wb = Workbook()
    ws = wb.active
    ws.title = "评论记录"
    ws.append(EXCEL_HEADERS)
    wb.save(excel_path)
    return wb


def load_existing_bvids(excel_path):
    """从Excel加载已评论的BVID集合"""
    if not os.path.exists(excel_path):
        return set()
    try:
        wb = load_workbook(excel_path, read_only=True)
        ws = wb.active
        bvids = set()
        for row in ws.iter_rows(min_row=2, values_only=True):  # 跳过表头
            if row and len(row) > 1 and row[1]:  # BVID在第2列
                bvids.add(str(row[1]))
        wb.close()
        return bvids
    except Exception as e:
        print(f"[WARN] 读取Excel失败: {e}，以空集合启动")
        return set()


def append_excel(excel_path, row_data, max_retries=3):
    """向Excel追加一条记录"""
    for attempt in range(max_retries):
        try:
            if os.path.exists(excel_path):
                wb = load_workbook(excel_path)
            else:
                wb = Workbook()
                ws = wb.active
                ws.title = "评论记录"
                ws.append(EXCEL_HEADERS)
            ws = wb.active
            ws.append(row_data)
            wb.save(excel_path)
            wb.close()
            return True
        except PermissionError:
            print(f"  [WARN] Excel文件被占用，等待3秒后重试 ({attempt+1}/{max_retries})")
            time.sleep(3)
        except Exception as e:
            print(f"  [WARN] 写Excel失败: {e} ({attempt+1}/{max_retries})")
            time.sleep(3)
    print(f"  [ERROR] 写Excel失败，记录丢失: {row_data}")
    return False


# ============== 主循环 ==============

def run_round(cookie_str, pairs, excel_path, existing_bvids, message, count, keyword):
    """跑一轮：搜索→评论→记录"""
    print(f"\n{'='*60}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始新一轮")
    print(f"  目标: 评论{count}个视频 | 关键词: {keyword} | 内容: {message}")
    print(f"  已评论总数: {len(existing_bvids)}")

    # 1. 搜索最新视频
    print(f"\n[1/3] 搜索最新视频...")
    videos = search_latest_videos(cookie_str, keyword, count, existing_bvids)
    print(f"  收集到 {len(videos)} 个未评论的新视频")

    if not videos:
        print("  没有新视频可评论，等待下一轮")
        return 0

    # 2. 逐个评论
    print(f"\n[2/3] 开始评论...")
    success_count = 0
    for i, v in enumerate(videos, 1):
        bvid = v["bvid"]
        aid = v["aid"]
        title = v["title"][:30]
        author = v["author"]

        print(f"  [{i}/{len(videos)}] {bvid} {title} by {author}")

        success, rpid, err = post_comment(cookie_str, pairs, bvid, aid, message)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if success:
            success_count += 1
            existing_bvids.add(bvid)
            print(f"    ✓ 成功 rpid={rpid}")
            append_excel(excel_path, [now, bvid, aid, title, author, message, "成功", rpid, ""])
        else:
            print(f"    ✗ 失败: {err}")
            append_excel(excel_path, [now, bvid, aid, title, author, message, "失败", "", err])
            # Cookie过期，直接退出
            if "Cookie过期" in err:
                print("\n[FATAL] Cookie已过期，程序退出。请重新登录后重启。")
                sys.exit(1)

        # 随机延迟 1-3秒
        delay = random.uniform(1, 3)
        time.sleep(delay)

    # 3. 统计
    print(f"\n[3/3] 本轮完成:")
    print(f"  成功: {success_count}/{len(videos)}")
    print(f"  累计已评论: {len(existing_bvids)}")
    print(f"  Excel: {excel_path}")

    return success_count


def main():
    parser = argparse.ArgumentParser(description="B站自动评论机器人")
    parser.add_argument("--count", type=int, default=100, help="每轮评论视频数量 (默认100)")
    parser.add_argument("--interval", type=int, default=300, help="每轮间隔秒数 (默认300=5分钟)")
    parser.add_argument("--once", action="store_true", help="只跑一轮就退出")
    parser.add_argument("--message", type=str, default="行", help="评论内容 (默认'行')")
    parser.add_argument("--excel", type=str, default=DEFAULT_EXCEL, help=f"Excel文件路径 (默认{DEFAULT_EXCEL})")
    parser.add_argument("--keyword", type=str, default="的", help="搜索关键词 (默认'的')")
    args = parser.parse_args()

    # 加载Cookie
    pairs, cookie_str = load_cookie()
    print(f"[OK] Cookie 加载成功")

    # 初始化Excel
    init_excel(args.excel)
    existing_bvids = load_existing_bvids(args.excel)
    print(f"[OK] Excel 初始化: {args.excel}")
    print(f"[OK] 已评论记录: {len(existing_bvids)} 条")

    # 主循环
    round_num = 0
    while True:
        round_num += 1
        print(f"\n{'#'*60}")
        print(f"# 第 {round_num} 轮")
        print(f"{'#'*60}")

        run_round(
            cookie_str, pairs, args.excel, existing_bvids,
            args.message, args.count, args.keyword
        )

        if args.once:
            print("\n[--once] 只跑一轮，退出")
            break

        print(f"\n[等待] {args.interval}秒后开始下一轮...")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
