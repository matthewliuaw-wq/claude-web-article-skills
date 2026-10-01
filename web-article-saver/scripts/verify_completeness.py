#!/usr/bin/env python3
"""校验文章「内容完整性」——抓 verify_image_references.py 抓不到的两类静默失败。

用法:
    python3 verify_completeness.py <文章目录> [<文章目录> ...]

verify_image_references.py 只管「媒体引用是否齐全」(坏链 / 孤儿),
但它查不出正文被悄悄概括、翻译被压缩、视频漏下载——这些是「静默失败」:
没有报错、没有坏链,内容就是变少了。本脚本补这个缺口,三个维度:

  A. 翻译结构对齐(无需基准,同时有英文原文+中文翻译即跑):
     对比段落数 / 图片引用数 / 列表项数,且只对「中文 < 英文」的丢失方向告警
     (漏段 / 漏图 / 概括);中文多于英文通常是翻译增值(加总结 / 拆步骤),不报。
     ⚠️ 不用「字符数比例」——中英文信息密度天然差 2-5 倍(中文一字一字符、
     英文一词多字符),逐段忠实翻译的中文也只有英文 40% 字符,会大量误报。

  B. 正文长度保真(需基准 _source-meta.json):
     主正文 md 的纯文本字符数 / 抓取时记录的 source_text_chars < 阈值
     → 疑似在「抓取→成型」之间被概括 / 截断。
     (同语言对比,密度一致,比例有效;跨语言无效,故只对「原文级」md 跑)

  C. 媒体数量(需基准 _source-meta.json):
     抓取时页面检测到的 video / img 元素数 vs 实际下载的文件数。
     页面有 3 个视频、images/ 只有 1 个 mp4 → 漏检 / 漏下载。

依赖基准(B/C)的检查:无 _source-meta.json 时跳过并提示。
退出码:有任何告警返回 1,全部正常 0 —— 可作收尾硬门控。

注:strip_to_text() 的纯文本提取逻辑必须与 write_source_meta.py 保持一致,
否则 B 检查的对比基准不可比。
"""
import json
import os
import re
import sys

THRESH_TEXT_RATIO = 0.70    # 检查B:正文纯文本 / 基准 < 0.70 告警
THRESH_STRUCT_RATIO = 0.25  # 检查A:结构项相对偏差 > 25% 告警
META_FILE = "_source-meta.json"

IMG_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg")
VID_EXTS = (".mp4", ".mov", ".webm")

# ---- 共享的纯文本提取(与 write_source_meta.py 保持一致)----
CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)
IMG_REF = re.compile(r"!\[[^\]]*\]\([^)]*\)")
HTML_TAG = re.compile(r"<[^>]+>")
INLINE_CODE = re.compile(r"`[^`]*`")
MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")          # [text](url) -> text
# 行首 markdown 标记:# 标题、> 引用、- * + 列表、| 表格。不含数字(避免误吞 "2026 年")
LINE_MARKS = re.compile(r"^[#>\-*+|]+\s*", re.MULTILINE)


def strip_to_text(content):
    """去 markdown 标记,返回纯文本(用于字符数对比)。"""
    s = CODE_FENCE.sub("", content)
    s = IMG_REF.sub("", s)
    s = HTML_TAG.sub("", s)
    s = MD_LINK.sub(r"\1", s)
    s = INLINE_CODE.sub("", s)
    s = LINE_MARKS.sub("", s)
    s = re.sub(r"\s+", "", s)        # 去所有空白,数实质字符
    return s


def text_chars(content):
    return len(strip_to_text(content))


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def count_local_images(content):
    """本地图片引用数(排除 http/data/blob)。"""
    refs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", content) \
         + re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', content, re.I)
    return sum(1 for r in refs if not r.startswith(("http://", "https://", "data:", "blob:")))


def count_list_items(content):
    return len(re.findall(r"^\s*(?:[-*+]|\d+\.)\s+\S", content, re.MULTILINE))


def count_paragraphs(content):
    c = CODE_FENCE.sub("\n", content)
    blocks = re.split(r"\n\s*\n", c)
    return sum(1 for b in blocks if re.search(r"\S", b))


def find_main_text_md(root, md_files):
    """主正文 md(原文级):优先 英文原文.md / 原文.md;否则只在【顶层目录】取最大非翻译 md。
    导读/校对报告在 文章导读/ 子目录,是改写衍生物,绝不纳入对比——
    否则改写后的导读会顶替原文,污染「正文长度保真」的基准对比。"""
    for name in ("英文原文.md", "原文.md"):
        p = os.path.join(root, name)
        if os.path.isfile(p):
            return p
    root_n = os.path.normpath(root)
    cands = [m for m in md_files
             if os.path.normpath(os.path.dirname(m)) == root_n          # 仅顶层,排除子目录衍生物
             and os.path.basename(m) not in ("中文翻译.md", "说明.md", "_source-text.md")
             and not os.path.basename(m).startswith("_")]
    if not cands:
        return None
    return max(cands, key=lambda m: os.path.getsize(m))


def check_translation_align(root, problems):
    """检查A:英文原文 vs 中文翻译 的结构对齐。
    原文命名不统一(英文原文.md / 原文.md / 文章同名.md),都识别——否则会漏检。"""
    tr = os.path.join(root, "中文翻译.md")
    if not os.path.isfile(tr):
        return  # 无翻译,跳过
    en = None
    for name in ("英文原文.md", "原文.md"):  # 优先标准命名
        p = os.path.join(root, name)
        if os.path.isfile(p):
            en = p
            break
    if not en:  # 兜底:顶层任意正文 md(排除翻译/说明/基准/导读)
        for fn in sorted(os.listdir(root)):
            full = os.path.join(root, fn)
            if (fn.endswith(".md") and os.path.isfile(full)
                    and fn not in ("中文翻译.md", "说明.md") and not fn.startswith("_")):
                en = full
                break
    if not en:
        return
    ec, tc = read(en), read(tr)
    metrics = {
        "段落": (count_paragraphs(ec), count_paragraphs(tc)),
        "图片": (count_local_images(ec), count_local_images(tc)),
        "列表项": (count_list_items(ec), count_list_items(tc)),
    }
    diffs = []
    for name, (ev, tv) in metrics.items():
        # 单向告警:只抓「中文 < 英文」的丢失方向(漏段/漏图/概括)。
        # 中文多于英文通常是翻译增值(加总结 / 拆步骤),不视为问题。
        if ev > 0 and tv < ev * (1 - THRESH_STRUCT_RATIO):
            diffs.append(f"{name} 英{ev}→中{tv}")
    if diffs:
        problems.append(
            f"翻译结构偏差({', '.join(diffs)})——疑似翻译时漏段/漏图/被概括,请对照英文原文核对"
        )


def check_text_fidelity(main_md, meta, problems):
    """检查B:主正文纯文本字符数 / 基准 source_text_chars。"""
    base = meta.get("source_text_chars")
    if not base or base < 100:
        return
    chars = text_chars(read(main_md))
    ratio = chars / base
    if ratio < THRESH_TEXT_RATIO:
        problems.append(
            f"正文疑似被概括/截断:主正文纯文本 {chars} 字符 / 抓取基准 {base} = {ratio:.0%} "
            f"(阈值 {THRESH_TEXT_RATIO:.0%})——回抓取步骤核对是否完整保留原文"
        )


def check_media_count(root, meta, problems):
    """检查C:页面检测的 video/img 数 vs 实际下载文件数。"""
    sv = meta.get("source_video_count", 0) or 0
    si = meta.get("source_img_count", 0) or 0
    if sv == 0 and si == 0:
        return
    have = {"img": 0, "vid": 0}
    for dp, _dn, fns in os.walk(root):
        for fn in fns:
            path = os.path.join(dp, fn)
            try:
                if os.path.getsize(path) < 1000:   # 跳过空文件 / 失败残留(否则会凑数骗过数量检查)
                    continue
            except OSError:
                continue
            ext = os.path.splitext(fn)[1].lower()
            if ext in IMG_EXTS:
                have["img"] += 1
            elif ext in VID_EXTS:
                have["vid"] += 1
    if sv and have["vid"] < sv:
        problems.append(f"视频漏下载:抓取时页面检测到 {sv} 个视频,实际仅 {have['vid']} 个视频文件")
    if si and have["img"] < si:
        problems.append(f"图片漏下载:抓取时页面检测到 {si} 张,实际仅 {have['img']} 张图片文件")


def check_dir(root):
    print(f"\n{'='*60}\n📁 {root}\n{'='*60}")
    if not os.path.isdir(root):
        print("  ❌ 目录不存在")
        return 1

    md_files = []
    for dp, _dn, fns in os.walk(root):
        for fn in fns:
            if fn.endswith(".md"):
                md_files.append(os.path.join(dp, fn))

    meta_path = os.path.join(root, META_FILE)
    meta = {}
    has_meta = os.path.isfile(meta_path)
    if has_meta:
        try:
            meta = json.loads(read(meta_path))
        except Exception as e:
            print(f"  ⚠️ 基准文件 {META_FILE} 解析失败:{e}")

    problems = []

    # 检查A:翻译对齐(无基准也跑)
    check_translation_align(root, problems)

    # 检查B/C:需基准
    if has_meta and meta:
        main_md = find_main_text_md(root, md_files)
        if main_md:
            check_text_fidelity(main_md, meta, problems)
        check_media_count(root, meta, problems)
    else:
        print(f"  ℹ️ 无 {META_FILE}——跳过「正文长度保真 / 媒体数量」检查(翻译对齐已跑)")
        print(f"     新文章抓取时落基准即可启用全部维度")

    if not problems:
        scope = "全部维度" if (has_meta and meta) else "仅翻译对齐维度"
        print(f"  ✅ 内容完整性正常({scope})")
    else:
        print(f"\n  🚫 {len(problems)} 个完整性问题:")
        for p in problems:
            print(f"     - {p}")
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


if __name__ == "__main__":
    main()
