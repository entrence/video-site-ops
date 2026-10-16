#!/usr/bin/env python3
"""将 .bilibili-cookie (纯字符串格式) 转为 yt-dlp 可用的 Netscape 格式。

读取:  ~/.bilibili-cookie  (格式: SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx)
       (可能有 "1|" 前缀，自动去除)
输出:  /tmp/bili_netscape_cookie.txt  (Netscape HTTP Cookie File)
"""
import sys, os

SRC = "~/.bilibili-cookie"
DST = "/tmp/bili_netscape_cookie.txt"

def main():
    if not os.path.exists(SRC):
        print(f"[ERROR] Cookie 文件不存在: {SRC}", file=sys.stderr)
        sys.exit(1)

    raw = open(SRC).read().strip()

    # 去除可能的 "1|" 前缀（某些写入方式会加）
    if "|" in raw:
        raw = raw.split("|", 1)[1]

    # 解析键值对
    pairs = {}
    for part in raw.split("; "):
        if "=" in part:
            k, v = part.split("=", 1)
            pairs[k.strip()] = v.strip()

    if "SESSDATA" not in pairs:
        print(f"[ERROR] Cookie 文件中未找到 SESSDATA，内容可能异常", file=sys.stderr)
        sys.exit(1)

    # 写 Netscape 格式
    lines = ["# Netscape HTTP Cookie File\n"]
    for name in ["SESSDATA", "bili_jct", "DedeUserID"]:
        if name in pairs:
            lines.append(f".bilibili.com\tTRUE\t/\tFALSE\t0\t{name}\t{pairs[name]}\n")

    with open(DST, "w") as f:
        f.writelines(lines)

    print(f"Netscape cookie 已写入: {DST}")
    print(f"yt-dlp 用法: yt-dlp --cookies {DST} -o '%(title)s.%(ext)s' <B站URL>")

if __name__ == "__main__":
    main()
