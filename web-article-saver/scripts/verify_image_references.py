#!/usr/bin/env python3
"""校验文章目录中图片/视频引用的完整性（双向）。

用法:
    python3 verify_image_references.py <文章目录> [<文章目录> ...]

这是 web-article-saver / web-article-processor 的强制收尾门控脚本。
做两件单向校验做不到的事：

  - 反向（查漏插，最关键）：images/ 里已下载的每张图/视频，是否都被某个 md 引用。
        未被任何 md 引用 = 孤儿媒体 = "下载了却没插进正文"，必须回锚点法补插。
  - 正向（查坏链）：md 里引用的每个本地媒体文件，是否真实存在。不存在 = 坏链。

退出码：发现任何问题返回 1，全部正常返回 0 —— 可作为流程收尾的硬门控。
"""
import os
import re
import sys

IMG_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.mp4', '.mov', '.webm'}
MD_IMG = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')
HTML_SRC = re.compile(r'<(?:img|video|source)[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)


def is_remote(p):
    return p.startswith(('http://', 'https://', 'data:', 'mailto:', 'blob:'))


def collect_media(root):
    """递归收集 root 下所有媒体文件（相对 root 的路径集合）。"""
    media = set()
    for dp, _dn, fns in os.walk(root):
        for fn in fns:
            if os.path.splitext(fn)[1].lower() in IMG_EXTS:
                media.add(os.path.relpath(os.path.join(dp, fn), root))
    return media


def md_local_refs(md_path):
    """返回该 md 中所有【本地】媒体引用路径（未去锚点/参数的原始串）。"""
    with open(md_path, encoding='utf-8') as f:
        content = f.read()
    refs = MD_IMG.findall(content) + HTML_SRC.findall(content)
    out = []
    for r in refs:
        if is_remote(r):
            continue
        r = r.strip().split('#')[0].split('?')[0]
        if r:
            out.append(r)
    return out


def check_dir(root):
    print(f"\n{'='*60}\n📁 {root}\n{'='*60}")
    if not os.path.isdir(root):
        print("  ❌ 目录不存在")
        return 1

    md_files = []
    for dp, _dn, fns in os.walk(root):
        for fn in fns:
            if fn.lower().endswith('.md'):
                md_files.append(os.path.join(dp, fn))
    media = collect_media(root)
    print(f"  📄 md 文件 {len(md_files)} 个 | 🖼️ 媒体文件 {len(media)} 个\n")

    referenced_basenames = set()
    bad_links = []
    for md in md_files:
        rel = os.path.relpath(md, root)
        local = md_local_refs(md)
        md_dir = os.path.dirname(md)
        for r in local:
            referenced_basenames.add(os.path.basename(r))
            full = os.path.normpath(os.path.join(md_dir, r))
            if not os.path.exists(full):
                bad_links.append((rel, r))
        print(f"  📄 {rel}: 本地媒体引用 {len(local)} 个")

    media_basenames = {os.path.basename(m) for m in media}
    orphans = media_basenames - referenced_basenames

    problems = 0
    if bad_links:
        problems += len(bad_links)
        print(f"\n  ❌ 坏链（md 引用但文件不存在）: {len(bad_links)} 处")
        for md, r in bad_links:
            print(f"     - {md} → {r}")
    if orphans:
        problems += len(orphans)
        print(f"\n  ⚠️ 孤儿媒体（已下载但未被任何 md 引用 = 漏插入）: {len(orphans)} 个")
        for o in sorted(orphans):
            print(f"     - {o}")

    if problems == 0:
        print("\n  ✅ 全部正常：无坏链、无孤儿媒体，图片引用完整。")
    else:
        print(f"\n  🚫 共 {problems} 个问题。孤儿媒体需回锚点法补插；坏链需修正引用路径。")
    return 1 if problems else 0


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(2)
    rc = 0
    for d in args:
        if check_dir(d) != 0:
            rc = 1
    sys.exit(rc)


if __name__ == '__main__':
    main()
