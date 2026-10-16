#!/usr/bin/env python3
"""
B站日报 - 数据拉取脚本
从B站API拉取今日热门视频数据，输出为 JSON 供 PPT 生成脚本使用

数据源:
  1. 热门视频流 (popular) - 无需Cookie, 最多100条
  2. 全站排行榜 (ranking/v2) - 无需Cookie, 100条
合并去重后按分区统计热度, 输出综合热度TOP10/播放TOP5/互动率TOP3
"""
import urllib.request, json, time, sys, os, hashlib
from collections import Counter, defaultdict
import datetime

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
OUTPUT_DIR = "~/bilibili-daily"
IMG_DIR = os.path.join(OUTPUT_DIR, "images")  # 封面和头像缓存目录


def download_image(url, kind="cover"):
    """下载图片到本地缓存, 返回本地路径。kind=cover/face"""
    if not url:
        return None
    # B站封面走 http 会 302 到 https, 且防盗链检查 Referer
    if url.startswith("http://"):
        url = "https://" + url[7:]
    # 用URL hash做文件名避免重复下载
    ext = ".jpg"
    if ".png" in url:
        ext = ".png"
    if ".webp" in url:
        ext = ".webp"
    fname = hashlib.md5(url.encode()).hexdigest() + ext
    fpath = os.path.join(IMG_DIR, f"{kind}_{fname}")
    if os.path.exists(fpath):
        return fpath  # 缓存命中
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", UA)
        req.add_header("Referer", "https://www.bilibili.com")
        resp = urllib.request.urlopen(req, timeout=10)
        data = resp.read()
        if len(data) < 100:
            return None
        with open(fpath, "wb") as f:
            f.write(data)
        return fpath
    except Exception as e:
        print(f"   图片下载失败 {kind}: {e}")
        return None

def fetch(url):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", UA)
    req.add_header("Referer", "https://www.bilibili.com")
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read().decode())

def fmt_num(n):
    if n >= 1e8: return f"{n/1e8:.1f}亿"
    if n >= 1e4: return f"{n/1e4:.1f}万"
    return str(n)

def heat_score(stat):
    """综合热度: 播放 + 点赞×5 + 投币×10 + 收藏×3 + 分享×8 + 评论×3"""
    return (stat.get('view',0) + stat.get('like',0)*5 + stat.get('coin',0)*10
            + stat.get('favorite',0)*3 + stat.get('share',0)*8 + stat.get('reply',0)*3)

def interact_rate(v):
    s = v['stat']
    total = s.get('like',0)+s.get('coin',0)+s.get('favorite',0)+s.get('reply',0)+s.get('share',0)
    return total / max(s.get('view',1), 1)

def main():
    today = datetime.date.today().strftime("%Y-%m-%d")
    print(f">> B站日报数据拉取 - {today}")

    # 1. 热门视频流 (5页=100条)
    all_popular = []
    for pn in range(1, 6):
        try:
            d = fetch(f"https://api.bilibili.com/x/web-interface/popular?ps=20&pn={pn}")
            if d['code'] == 0:
                vids = d['data']['list']
                all_popular.extend(vids)
                if d['data'].get('no_more'):
                    break
            time.sleep(1)
        except Exception as e:
            print(f"   popular第{pn}页失败: {e}")
            break
    print(f"   热门流: {len(all_popular)}条")

    # 2. 全站排行榜
    time.sleep(1)
    try:
        rank_data = fetch("https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all")
        all_rank = rank_data['data']['list'] if rank_data['code'] == 0 else []
    except Exception as e:
        print(f"   排行榜失败: {e}")
        all_rank = []
    print(f"   排行榜: {len(all_rank)}条")

    # 3. 合并去重
    seen = set()
    merged = []
    for v in all_rank:
        seen.add(v['bvid'])
        merged.append(v)
    for v in all_popular:
        if v['bvid'] not in seen:
            seen.add(v['bvid'])
            merged.append(v)
    print(f"   合并去重: {len(merged)}条")

    if not merged:
        print("!! 无数据，退出")
        sys.exit(1)

    # 4. 分区统计
    region_count = Counter()
    region_play = defaultdict(int)
    for v in merged:
        tname = v.get('tname', '未知')
        stat = v.get('stat', {})
        region_count[tname] += 1
        region_play[tname] += stat.get('view', 0)

    # 5. 组装数据结构
    data = {
        "date": today,
        "total_popular": len(all_popular),
        "total_rank": len(all_rank),
        "total_merged": len(merged),
        "regions_by_count": [
            {"name": n, "count": c, "play": region_play[n]}
            for n, c in region_count.most_common(10)
        ],
        "regions_by_play": [
            {"name": n, "play": p}
            for n, p in sorted(region_play.items(), key=lambda x: x[1], reverse=True)[:5]
        ],
        "top10_heat": [],
        "top5_play": [],
        "top3_interact": [],
    }

    for v in sorted(merged, key=lambda x: heat_score(x.get('stat',{})), reverse=True)[:10]:
        s = v['stat']
        data["top10_heat"].append({
            "title": v['title'][:35], "bvid": v['bvid'],
            "view": s.get('view',0), "like": s.get('like',0), "coin": s.get('coin',0),
            "favorite": s.get('favorite',0), "reply": s.get('reply',0), "share": s.get('share',0),
            "up": v['owner']['name'], "region": v.get('tname','?'),
            "heat": heat_score(s)
        })

    for v in sorted(merged, key=lambda x: x.get('stat',{}).get('view',0), reverse=True)[:5]:
        s = v['stat']
        data["top5_play"].append({
            "title": v['title'][:35], "bvid": v['bvid'],
            "view": s.get('view',0), "like": s.get('like',0),
            "up": v['owner']['name'], "region": v.get('tname','?')
        })

    inter_candidates = [v for v in merged if v.get('stat',{}).get('view',0) > 100000]
    for v in sorted(inter_candidates, key=interact_rate, reverse=True)[:3]:
        s = v['stat']
        data["top3_interact"].append({
            "title": v['title'][:35], "bvid": v['bvid'],
            "view": s.get('view',0), "up": v['owner']['name'],
            "region": v.get('tname','?'), "rate": round(interact_rate(v)*100, 1)
        })

    # 6. 下载封面和头像
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(IMG_DIR, exist_ok=True)

    print(">> 下载视频封面和UP主头像...")

    def add_images(item, v):
        """为数据项添加封面和头像本地路径"""
        cover_url = v.get('pic', '')
        face_url = v.get('owner', {}).get('face', '')
        item['cover_path'] = download_image(cover_url, "cover")
        item['face_path'] = download_image(face_url, "face")
        return item

    # 重新组装带图片路径的数据
    for item, v in zip(data["top10_heat"],
                       sorted(merged, key=lambda x: heat_score(x.get('stat',{})), reverse=True)[:10]):
        add_images(item, v)

    for item, v in zip(data["top5_play"],
                       sorted(merged, key=lambda x: x.get('stat',{}).get('view',0), reverse=True)[:5]):
        add_images(item, v)

    for item, v in zip(data["top3_interact"],
                       sorted(inter_candidates, key=interact_rate, reverse=True)[:3]):
        add_images(item, v)

    # 统计图片下载情况
    all_items = data["top10_heat"] + data["top5_play"] + data["top3_interact"]
    covers_ok = sum(1 for i in all_items if i.get('cover_path'))
    faces_ok = sum(1 for i in all_items if i.get('face_path'))
    print(f"   封面: {covers_ok}/{len(all_items)}, 头像: {faces_ok}/{len(all_items)}")

    # 7. 保存
    data_path = os.path.join(OUTPUT_DIR, "data.json")
    with open(data_path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f">> 数据已保存: {data_path}")
    return data_path

if __name__ == "__main__":
    main()
