#!/usr/bin/env python3
"""Download images from WeChat articles with anti-hotlink bypass.

Usage:
    python3 download_images.py <url_list_file> <output_dir> [--referer URL]

The url_list_file should contain one image URL per line.
Downloads are done with Referer header to bypass WeChat CDN anti-hotlinking.
"""
import subprocess, sys, os, hashlib, argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

def download_one(url, outpath, referer):
    r = subprocess.run(
        ["curl", "-sL", "-o", outpath, "-H", f"Referer: {referer}", url],
        capture_output=True, timeout=30
    )
    if r.returncode != 0:
        return False, f"curl exit {r.returncode}"
    size = os.path.getsize(outpath)
    if size < 300:
        os.remove(outpath)
        return False, f"too small ({size}B, likely blocked)"
    # Validate image header
    with open(outpath, 'rb') as f:
        header = f.read(4)
    if not (header[:2] == b'\xff\xd8' or header[:4] == b'\x89PNG' or header[:4] == b'GIF8'):
        os.remove(outpath)
        return False, f"invalid header ({header.hex()})"
    return True, f"{size//1024}KB"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("url_list_file")
    p.add_argument("output_dir")
    p.add_argument("--referer", required=True)
    p.add_argument("--concurrency", type=int, default=10)
    args = p.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    with open(args.url_list_file) as f:
        urls = [line.strip() for line in f if line.strip()]

    ok = fail = dup = 0
    seen_hashes = {}

    def task(item):
        idx, url = item
        ext = ".gif" if "wx_fmt=gif" in url else (".png" if "wx_fmt=png" in url else ".jpg")
        fname = f"img-{idx+1:02d}{ext}"
        outpath = os.path.join(args.output_dir, fname)
        success, msg = download_one(url, outpath, args.referer)
        if success:
            h = hashlib.md5(open(outpath,'rb').read()).hexdigest()
            return idx, True, fname, msg, h
        return idx, False, fname, msg, None

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = {pool.submit(task, item): item for item in enumerate(urls)}
        for fut in as_completed(futures):
            idx, success, fname, msg, h = fut.result()
            if success:
                if h in seen_hashes:
                    dup += 1
                    # Keep file but note it's a duplicate
                else:
                    seen_hashes[h] = fname
                ok += 1
            else:
                fail += 1
            print(f"  {'OK' if success else 'FAIL'} {fname}: {msg}")

    print(f"\nDone: {ok} ok, {fail} failed, {dup} duplicates")
    return 0 if fail == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
