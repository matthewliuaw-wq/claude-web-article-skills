#!/usr/bin/env python3
"""抓取阶段落基准:读源正文,算纯文本字符数,生成 _source-meta.json。

在「抓取→成型 md」之间,正文可能被悄悄概括/截断——这是静默失败,事后
(verify_image_references.py)查不出。本脚本在抓取瞬间把源正文长度 + 页面媒体数
落盘为基准,供 verify_completeness.py 收尾对比。

用法(抓取后立刻跑):
    # 1. 先把抓取返回的原始正文原样存为 _source-text.md
    #    (webReader 的 markdown / walker 返回的 text / snapshot 的 text,未加工)
    # 2. 再跑:
    python3 write_source_meta.py <文章目录> \
        --url "https://..." --title "..." --method walker \
        --videos 3 --imgs 8

默认读 <文章目录>/_source-text.md。也可用 --text 指定别的源文件(会被复制为 _source-text.md 留底)。

strip_to_text() 必须与 verify_completeness.py 保持一致。
"""
import argparse
import json
import os
import re
import shutil
import sys

META_FILE = "_source-meta.json"
TEXT_FILE = "_source-text.md"
TEXT_RATIO_NOTE = 0.70

CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)
IMG_REF = re.compile(r"!\[[^\]]*\]\([^)]*\)")
HTML_TAG = re.compile(r"<[^>]+>")
INLINE_CODE = re.compile(r"`[^`]*`")
MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
LINE_MARKS = re.compile(r"^[#>\-*+|]+\s*", re.MULTILINE)


def strip_to_text(content):
    s = CODE_FENCE.sub("", content)
    s = IMG_REF.sub("", s)
    s = HTML_TAG.sub("", s)
    s = MD_LINK.sub(r"\1", s)
    s = INLINE_CODE.sub("", s)
    s = LINE_MARKS.sub("", s)
    s = re.sub(r"\s+", "", s)
    return s


def main():
    ap = argparse.ArgumentParser(description="抓取阶段落基准 _source-meta.json")
    ap.add_argument("directory", help="文章目录")
    ap.add_argument("--text", help="源正文文件(默认 <目录>/_source-text.md)")
    ap.add_argument("--url", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--method", default="", help="抓取方式:walker / webReader / snapshot")
    ap.add_argument("--videos", type=int, default=0, help="页面内 video 元素数")
    ap.add_argument("--imgs", type=int, default=0, help="页面正文实质图片数")
    args = ap.parse_args()

    root = args.directory.rstrip("/")
    if not os.path.isdir(root):
        print(f"❌ 目录不存在: {root}", file=sys.stderr)
        sys.exit(2)

    text_path = os.path.join(root, TEXT_FILE)
    if args.text and os.path.abspath(args.text) != os.path.abspath(text_path):
        shutil.copyfile(args.text, text_path)
        print(f"📋 已复制源正文 → {text_path}")
    if not os.path.isfile(text_path):
        print(f"❌ 找不到源正文: {text_path}\n"
              f"   请先把抓取返回的原始正文(未加工)原样写入 {TEXT_FILE}", file=sys.stderr)
        sys.exit(2)

    with open(text_path, encoding="utf-8") as f:
        content = f.read()
    chars = len(strip_to_text(content))

    meta = {
        "source_url": args.url,
        "source_title": args.title,
        "fetch_method": args.method,
        "source_text_chars": chars,
        "source_text_file": TEXT_FILE,
        "source_video_count": args.videos,
        "source_img_count": args.imgs,
    }
    meta_path = os.path.join(root, META_FILE)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"✅ 基准已落盘: {meta_path}")
    print(f"   源正文纯文本 {chars} 字符 | 视频 {args.videos} | 图片 {args.imgs} | 方式 {args.method or '(未填)'}")
    print(f"   收尾时 verify_completeness.py 将据此对比最终 md"
          f"(正文 < {int(TEXT_RATIO_NOTE * 100)}% 基准 = 概括告警)")


if __name__ == "__main__":
    main()
