---
name: web-article-saver
description: 将网页文章完整保存为本地 Markdown + 图片 + 视频。支持微信公众号（mp.weixin.qq.com）、X/Twitter（x.com，含长文章）、普通博客等。自动抓取正文、下载所有图片（绕过防盗链）和视频（X 视频通过 ffmpeg 合并 HLS 流、微信内嵌视频直链下载）、登录墙/反爬源（如 X 长文章 x.com/i/article）正文用 Playwright MCP 抓取、生成图文混排的 md 文件，并用双脚本校验收尾（媒体引用完整性 + 防止正文被静默概括）。当用户提供 URL 要求保存文章、下载文章、存档、离线阅读时触发。关键词：保存文章、下载文章、文章存档、微信公众号、mp.weixin.qq.com、x.com、twitter、网页保存、下载视频、X长文章、article、登录墙、反爬、Playwright MCP。
---

# 网页文章保存器

将各类网页文章完整保存为 Markdown + 图片 + 视频文件。根据 URL 自动识别来源并选择对应策略。

## 环境依赖

本 skill 依赖 Playwright MCP 和 web_reader MCP。视频下载额外需要 **ffmpeg**（`brew install ffmpeg` 或 `apt install ffmpeg`）。首次使用时先读取 [references/mcp-setup.md](references/mcp-setup.md) 检查环境是否就绪，如果缺少依赖则提醒用户安装后再继续。

## 来源识别

| URL 模式 | 来源 | 难点 |
|----------|------|------|
| `mp.weixin.qq.com` | 微信公众号 | 懒加载 + 防盗链；内嵌视频（mpvideo）渲染后 `<video>` 暴露带签名 MP4 直链 |
| `x.com` / `twitter.com` | X/Twitter 推文 | 需滚动加载；视频为 HLS 分片流 |
| `x.com/i/article/<id>` | X 长文章（Premium） | **登录墙**：webReader 拿不到正文 → 用 Playwright MCP（见 ⭐ 节） |
| 任何返回登录页/空正文的源 | 登录墙 / 反爬站点 | webReader 失败 → **用 Playwright MCP**（见 ⭐ 节） |
| 其他 | 普通网页 | 通常直接下载即可 |

## ⭐ 登录墙 / 反爬源：改用 Playwright MCP

当 `web_reader` **拿不到正文**时——典型是 X 长文章（`x.com/i/article/<id>`，正文在登录墙后），或任何返回登录页 / 空正文 / 反爬拦截的源——**一律改用 Playwright MCP 的 `browser_*` 工具**，既抓正文又抓图。

🔴 **实战铁律（经多次验证）**：手写 node 脚本的 Playwright（`launchPersistentContext`，无论无头/有头/CDP 连真机 Chrome）**会被 X 反爬挡死**（带有效 cookie 也被重定向到登录页）。X 对 webdriver/CDP 自动化指纹极敏感。但 **Playwright MCP 的 `browser_*` 工具能通过**——MCP 浏览器指纹不同。**结论：这类源只走 MCP，绝不写 node 脚本。**

详细流程（X 长文章 walker 脚本用法、短推文 snapshot 替代方案、图片直链 curl）见 [references/anti-crawl.md](references/anti-crawl.md)。

## 工作流程

### 第一步：抓取全文

```
mcp__web_reader__webReader(url="文章URL", return_format="markdown", retain_images=false)
```

从结果中提取：标题、作者、正文、所有图片 URL。

> 🟢 **抓到正文后立即「落基准」（防静默概括，必做）**：把抓取返回的**原始未加工**正文原样存为 `<输出目录>/_source-text.md`，然后跑：
> ```bash
> python3 scripts/write_source_meta.py "<输出目录>" \
>   --url "文章URL" --title "标题" --method walker \
>   --videos <页面 video 元素数> --imgs <正文实质图片数>
> ```
> 这在抓取瞬间锁定「源正文长度 + 媒体数」。**没有它，正文若在后续被悄悄概括/截断，永远查不出**。收尾的 `verify_completeness.py` 靠它做对比（详见 [references/verification.md](references/verification.md)）。

> ⚠️ **若 webReader 返回登录页 / 空正文 / 反爬拦截**——立即跳到上面「⭐ 登录墙 / 反爬源」一节。别在 webReader 上空耗，也别手写 node 脚本 Playwright（会被反爬挡）。

### 第二步：提取媒体 URL（图片 + 视频，务必同时）

用 Playwright 获取浏览器中实际加载的图片和视频：

```
1. browser_navigate(url="文章URL")
2. browser_evaluate: 滚动整个页面触发懒加载
3. browser_evaluate: 提取图片 URL（见下方按来源调整）
4. browser_evaluate: 检测 video 元素，判断是否有视频
```

**图片提取 — 按来源调整：**

- **微信**：提取 `#js_content img` 的 `data-src` 或 `src`，过滤 `data:` 和 `sz_mmbiz_png` 中的 1x1 SVG。个别图 CDN 拒绝（返回 243B 占位符）时跳过 + 文字标注
- **X/Twitter**：提取 `article img[src*="pbs.twimg.com"]`，过滤头像（96x96）和 alt 含 "Avatar" 的图片
- **其他**：提取 `article img` 或 `main img`，过滤 tracking pixel（<10px）

**视频检测（与图片同时进行，极易漏）**：X 的图片（`pbs.twimg.com/media`）和视频（`<video>` 元素）是**独立的 DOM 元素**——抓图片时很容易漏掉视频。必须用 `browser_evaluate` 检测 `<video>`：记录 `poster`（其中的视频 ID 用于关联 m3u8）、纵向位置 `top`（触发懒加载 + 排序用）、`duration`。微信内嵌视频则记录 `<video>` 的 `src`（签名 MP4 直链）+ `poster`（封面）。检测代码见 [references/video-download.md](references/video-download.md)。

### 第三步：下载图片和视频

**图片：**

微信文章使用脚本带 Referer 头下载绕过防盗链：
```bash
python3 scripts/download_images.py /tmp/img_urls.txt <output_dir>/images/ --referer "文章URL"
```

X/Twitter 和其他网页直接 curl 下载（无防盗链，图片直链本身公开）：
```bash
curl -sL -H "User-Agent: Mozilla/5.0 ..." -H "Referer: https://x.com/" "<img_url>" -o img-01.jpg
```

下载后验证每个文件的图片头（JPEG/PNG/GIF）。

**视频（三类，按来源选择）：**

| 来源 | 形态 | 方法 |
|------|------|------|
| X/Twitter | HLS 分片流（m3u8） | 滚动+悬停触发加载 → 抓 master m3u8 → ffmpeg 合流 |
| 微信内嵌视频（mpvideo） | 渲染后 `<video>` src 即带签名 MP4 直链 | **立刻 curl**（签名有时效，拿到就下） |
| 普通网页 | 直链 `.mp4` | 直接 curl，无需 ffmpeg |

X 视频完整流程（懒加载触发的滚动+悬停代码、m3u8 捕获、ffmpeg 命令、失败重试顺序）与微信视频检测/下载代码，见 [references/video-download.md](references/video-download.md)。

### 第四步：生成 Markdown（图文混排，关键）

根据正文内容和下载的图片/视频生成完整 md 文件。头部包含元信息：

```markdown
# {标题}

> 来源：{作者/公众号名}
> 原文链接：{URL}
> 抓取方式：web_reader + Playwright MCP 工具
> 抓取时间：{日期}
```

**⚠️ 图片/视频必须按原文精确位置嵌入（最常见失败模式）**：

- **常见错误**：用 `innerText` 只拿到纯文本正文，然后把所有图片堆在文末或文首，或干脆忘了嵌——图文分离，存档丧失价值
- **正确做法（锚点法）**：下载图片时同步记录每张图在 DOM 中的精确位置——取它**后面紧跟的第一段正文文字**（≥15 字符）作为"后文锚点"；生成 md 时按锚点把图片插到对应段落之前。登录墙源走 walker 时更简单：正文里的 `[[IMG1]]..[[IMGn]]` 内联占位直接替换成 `![](images/img-0N.ext)`，位置天然与原文对齐
- 视频同理：用锚点法定位后插入 `<video controls width="100%" src="video-01.mp4"></video>`，前后加空行
- 生成后自查：`![](...)` 引用数 == 下载的图片数

**视频推文额外产物**：当推文内容主要是视频（文字很短）时，生成 `说明.md`（中英对照：推文原文 + 每个视频配封面图与双语描述 + 文件清单）。

记忆口诀：**下载即定位，定位即嵌入，嵌入即校验。**

### 第五步：校验（强制门控，两个脚本都 exit 0 才算完成）

```bash
python3 scripts/verify_image_references.py "<输出目录>"   # 媒体引用完整性（双向）
python3 scripts/verify_completeness.py "<输出目录>"       # 内容完整性（防静默概括）
```

1. **verify_image_references.py** — 双向核对：正向查坏链（md 引用的媒体是否存在）；反向查漏插（`images/` 里已下载的媒体是否都被 md 引用）。报告"孤儿媒体"= 下载了却没插进正文，必须回到第四步补插，重跑直到 exit 0
2. **verify_completeness.py** — 抓前者查不到的「静默失败」：翻译结构对齐（中文比英文少超阈值 = 漏段/概括）、正文长度保真（正文/抓取基准 <70% = 被概括/截断）、媒体数量（页面检测数 vs 实际下载数）

批量校验整个知识库目录用 `python3 scripts/check_all_articles.py <根目录>`。原理与各维度详见 [references/verification.md](references/verification.md)。

## 输出结构

```
<output_dir>/
├── {文章标题}.md
├── images/
│   ├── img-01.jpg
│   ├── img-02.png
│   └── ...
└── video-01.mp4          # 可选，仅当原文含视频时（多个则 video-02…）
```

## 注意事项

- 微信 CDN 防盗链：必须加 `Referer` 头，否则返回 243B 空内容
- X/Twitter 视频懒加载：默认不请求 m3u8，必须滚动到视频位置 + 悬停才加载流；且需已登录的 Playwright 会话（未登录只能看到封面图）
- 微信内嵌视频的 MP4 直链**带时效签名**，检测到就立刻下载，不要拖到后面
- 文件名中特殊字符（冒号、引号等）替换为下划线或省略
- 部分微信文章含付费内容，web_reader 可能只能获取摘要
- 长文正文抓取**优先用 walker 脚本而非 snapshot**：snapshot 的 yaml 无障碍树对长文是 59KB+，占用大量上下文且代码块/图位难还原；walker 紧凑十倍、图文位置天然对齐
