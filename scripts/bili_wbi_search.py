#!/usr/bin/env python3
"""
B站 WBI 签名搜索脚本
用法: python3 bili_wbi_search.py <keyword> [search_type] [page] [page_size]
search_type: video(默认) / bili_user / live_user
需要 ~/.bilibili-cookie 存在且有效

原理:
  B站搜索接口 /x/web-interface/wbi/search/type 需要 WBI 签名,
  否则返回 -403 或空结果。签名步骤:
  1. 从 nav 接口获取 wbi_img.img_url 和 wbi_img.sub_url
  2. 提取 URL 末尾文件名(去掉扩展名)作为 img_key / sub_key, 拼接为 raw_key
  3. 用固定 mixin table 对 raw_key 重排, 取前32字符得到 mixin_key
  4. 搜索参数加 wts(当前时间戳), 按 key 排序后 urlencode
  5. 拼接 mixin_key 后 MD5 得到 w_rid, 加入参数发送请求
"""

import urllib.request, urllib.parse, json, hashlib, time, sys, re, os

COOKIE_PATH = os.path.expanduser('~/.bilibili-cookie')

# WBI mixin key table (fixed, maintained by Bilibili)
MIXIN_KEY_ENC_TAB = [
    46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,
    33,9,8,10,15,48,41,44,17,39,12,34,7,45,3,19,21,29,62,46,25,
    55,60,23,15,52,11,57,56,21,38,53,48,62,16,13,1,35,28,26,42,
    59,10,22,30,13,50,40,4,20,36,57,55,48,4,20,24,39,51,37,11,
    61,29,14,36,43,2,6,17,40,16,37,31,12,39,6,9,25,32,26,55,
    3,31,53,24,9,11,47,7,31,60,12,27,49,47,8,6,5,41,47,41,
    49,59,2,50,0,23,43,44,24,59,39,56,34,14,18,40,24,60,14,46,
    2,37,43,2,51,22,0,45,39,7,43,2,40,2,49,25,26,38,3,5,
    63,33,5,22,38,48,43,44,9,4,34,22,39,10,42,43,32,2,2,1,
    25,17,4,50,48,32,57,3,20,36,10,58,20,10,35,52,22,51,22,53,
    23,34,35,9,4,5,51,15,51,61,12,16,8,28,22,7,22,57,23,56,
    45,40,32,19,32,31,49,43,31,4,12,31,20,45,12,33,33,22,35,
    32,29,1,31,13,41,19,10,53,16,15,38,21,22,13,9,49,21,51,63,
    1,6,9,48,56,17,2,38,0,31,36,21,13,54,7,45,8,35,41,53,
    45,52,16,53,51,24,2,5,7,2,6,32,33,29,23,6,39,11,8,24,
    36,65,36,68,56,49,59,65,32,33,28,9,31,24,0,31,28,36,71,68,
    71,60,60,50,9,36,34,33,65,33,50,31,42,49,49,52,53,66,52,49,
    61,56,6,60,27,42,63,40,8,6,33,52,63,42,40,23,33,52,35,
    19,28,49,0
]


def get_mixin_key(wbi_img_url, wbi_sub_url):
    """从 nav 接口获取的 img_url 和 sub_url 中提取 mixin key"""
    img_key = wbi_img_url.rsplit('/', 1)[1].split('.')[0]
    sub_key = wbi_sub_url.rsplit('/', 1)[1].split('.')[0]
    raw_key = img_key + sub_key
    return ''.join([raw_key[i] for i in MIXIN_KEY_ENC_TAB[:32]])


def wbi_sign(params, mixin_key):
    """对搜索参数进行 WBI 签名，返回带 w_rid 的完整参数"""
    params['wts'] = int(time.time())
    query = urllib.parse.urlencode(sorted(params.items()))
    w_rid = hashlib.md5((query + mixin_key).encode()).hexdigest()
    params['w_rid'] = w_rid
    return params


def search(keyword, search_type='video', page=1, page_size=20):
    """执行 B站 WBI 签名搜索，返回结果列表并打印格式化输出"""
    if not os.path.exists(COOKIE_PATH):
        print(f'错误: Cookie 文件不存在: {COOKIE_PATH}')
        print('请先加载 bilibili-cookie skill 并完成二维码登录')
        sys.exit(1)

    cookie = open(COOKIE_PATH).read().strip()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Cookie': cookie,
        'Referer': 'https://www.bilibili.com/'
    }

    # 1. 验证 Cookie + 获取 WBI keys
    nav_req = urllib.request.Request('https://api.bilibili.com/x/web-interface/nav', headers=headers)
    nav_resp = urllib.request.urlopen(nav_req, timeout=10)
    nav_data = json.loads(nav_resp.read().decode())

    if nav_data['code'] != 0:
        print(f'Cookie 验证失败 (code={nav_data["code"]}): {nav_data.get("message", "")}')
        print('Cookie 可能已过期，请重新加载 bilibili-cookie skill 扫码登录')
        sys.exit(1)

    print(f'Cookie 有效: {nav_data["data"]["uname"]} (UID: {nav_data["data"]["mid"]})')

    wbi_img = nav_data['data']['wbi_img']['img_url']
    wbi_sub = nav_data['data']['wbi_img']['sub_url']
    mixin_key = get_mixin_key(wbi_img, wbi_sub)

    # 2. 构造搜索参数并签名
    params = {
        'keyword': keyword,
        'search_type': search_type,
        'page': page,
        'page_size': page_size,
    }
    if search_type == 'video':
        params['order'] = 'totalrank'

    params = wbi_sign(params, mixin_key)

    # 3. 发送搜索请求
    url = f'https://api.bilibili.com/x/web-interface/wbi/search/type?{urllib.parse.urlencode(params)}'
    req = urllib.request.Request(url, headers=headers)
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read().decode())

    if data['code'] != 0:
        print(f'搜索失败: code={data["code"]} msg={data.get("message", "")}')
        sys.exit(1)

    results = data.get('data', {}).get('result', [])
    print(f'搜索到 {len(results)} 条结果\n')

    # 4. 格式化输出
    if search_type == 'bili_user':
        for u in results:
            print('---')
            print(f'UID: {u["mid"]}')
            print(f'名称: {u["uname"]}')
            print(f'签名: {u.get("usign", "")}')
            print(f'粉丝: {u.get("fans", 0)}  视频: {u.get("videos", 0)}')
            print(f'头像: {u.get("upic", "")}')
            print()
    elif search_type == 'video':
        for v in results:
            title = re.sub(r'<[^>]+>', '', v['title'])
            desc = re.sub(r'<[^>]+>', '', v.get('description', ''))
            print('---')
            print(f'标题: {title}')
            print(f'UP主: {v["author"]}  播放: {v.get("play", 0)}  BV: {v["bvid"]}')
            if desc:
                print(f'描述: {desc[:120]}')
            print()

    return results


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f'用法: python3 {sys.argv[0]} <keyword> [search_type] [page] [page_size]')
        print(f'search_type: video(默认) / bili_user / live_user')
        sys.exit(1)

    keyword = sys.argv[1]
    search_type = sys.argv[2] if len(sys.argv) > 2 else 'video'
    page = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    page_size = int(sys.argv[4]) if len(sys.argv) > 4 else 20

    search(keyword, search_type, page, page_size)
