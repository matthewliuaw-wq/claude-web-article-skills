---
name: web-article-saver
description: 将网页文章完整保存为本地 Markdown + 图片。支持微信公众号（mp.weixin.qq.com）、X/Twitter（x.com）、普通博客等。自动抓取正文、下载所有图片（绕过防盗链）、生成带图片引用的 md 文件并校验。当用户提供 URL 要求保存文章、下载文章、存档、离线阅读时触发。关键词：保存文章、下载文章、文章存档、微信公众号、mp.weixin.qq.com、x.com、twitter、网页保存。
---

# 网页文章保存器

将各类网页文章完整保存为 Markdown + 图片文件。根据 URL 自动识别来源并选择对应策略。

## 环境依赖

本 skill 依赖 Playwright MCP 和 web_reader MCP。首次使用时先读取 [references/mcp-setup.md](references/mcp-setup.md) 检查环境是否就绪，如果缺少依赖则提醒用户安装后再继续。

## 来源识别

| URL 模式 | 来源 | 难点 |
|----------|------|------|
| `mp.weixin.qq.com` | 微信公众号 | 懒加载 + 防盗链 |
| `x.com` / `twitter.com` | X/Twitter | 需滚动加载 |
| 其他 | 普通网页 | 通常直接下载即可 |

## 工作流程

### 第一步：抓取全文

```
mcp__web_reader__webReader(url="文章URL", return_format="markdown", retain_images=false)
```

从结果中提取：标题、作者、正文、所有图片 URL。

### 第二步：提取实际图片 URL

用 Playwright 获取浏览器中实际加载的图片：

```
1. browser_navigate(url="文章URL")
2. browser_evaluate: 滚动整个页面触发懒加载
3. browser_evaluate: 提取图片 URL
4. 过滤掉占位符、头像、1x1 SVG
```

**按来源调整提取逻辑：**

- **微信**：提取 `#js_content img` 的 `data-src` 或 `src`，过滤 `data:` 和 `sz_mmbiz_png` 中的 1x1 SVG
- **X/Twitter**：提取 `article img[src*="pbs.twimg.com"]`，过滤头像（96x96）和 alt 含 "Avatar" 的图片
- **其他**：提取 `article img` 或 `main img`，过滤 tracking pixel（<10px）

### 第三步：下载图片

**微信文章**：使用脚本带 Referer 头下载绕过防盗链：
```bash
python3 scripts/download_images.py /tmp/img_urls.txt <output_dir>/images/ --referer "文章URL"
```

**X/Twitter 和其他网页**：直接 curl 下载（无防盗链）：
```bash
# 批量下载，10 并发
for url in "${urls[@]}"; do curl -sL -o "<name>.jpg" "$url" & done; wait
```

下载后验证每个文件的图片头（JPEG/PNG/GIF）。

### 第四步：生成 Markdown

根据正文内容和下载的图片生成完整 md 文件。头部包含元信息：

```markdown
# {标题}

> 来源：{作者/公众号名}
> 原文链接：{URL}
> 抓取方式：web_reader + Playwright MCP 工具
> 抓取时间：{日期}
```

图片引用规则：
- 按原文出现顺序插入 `![](images/img-XX.jpg)`
- 装饰性小图标保留，原文重复出现就重复引用
- 代码块内容保留原格式（推文中常见提示词）
- 图表/截图前后加空行

### 第五步：校验

1. **图片完整性**：检查文件头是否为有效图片格式
2. **引用一致性**：确认 md 中引用的每张图片都存在于 images/ 目录
3. **正文覆盖率**：对比 web_reader 文本长度与 md 文件正文长度，偏差 >30% 则告警

## 输出结构

```
<output_dir>/
├── {文章标题}.md
└── images/
    ├── img-01.jpg
    ├── img-02.png
    └── ...
```

## 注意事项

- 微信 CDN 防盗链：必须加 `Referer` 头，否则返回 243B 空内容
- X/Twitter 无防盗链，但需要 Playwright 滚动加载
- 文件名中特殊字符（冒号、引号等）替换为下划线或省略
- 部分微信文章含付费内容，web_reader 可能只能获取摘要
