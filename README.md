# Claude Code Web Article Skills

两个 Claude Code Skills，把网页文章保存、翻译为完整的中文学习资料包。

与同类工具相比的三个核心差异：

1. **多源支持**——微信公众号（防盗链绕过）、X/Twitter（含登录墙后的 Premium 长文章）、普通博客，一套流程全覆盖
2. **完整的视频方案**——X 的 HLS 分片流自动合流、微信内嵌视频的签名直链下载、普通网页直链视频，三种来源都能落地为本地 `mp4`
3. **防概括校验门控**——抓取时锁定「源正文长度 + 媒体数」基准，收尾用两个校验脚本核对媒体引用完整性（双向）与内容完整性（防止正文在翻译/改写环节被悄悄概括截断），全绿才算交付

## web-article-saver

将网页文章完整保存为本地 Markdown + 图片 + 视频。

- **微信公众号**（mp.weixin.qq.com）— 自动绕过 CDN 防盗链（Referer 头），内嵌视频（mpvideo）直接下载带签名 MP4
- **X/Twitter**（x.com）— 滚动加载长推文串；视频用 ffmpeg 合并 HLS 流；Premium 长文章（登录墙后）经 Playwright MCP 抓取
- **登录墙 / 反爬源** — `web_reader` 拿不到正文时自动切换 Playwright MCP（含实战验证的反爬经验：为什么不能用自写 Playwright 脚本）
- **普通博客** — 直接抓取

内置校验系统：抓取时落基准（`_source-text.md` + `_source-meta.json`），收尾跑双校验脚本（详见 `web-article-saver/references/verification.md`）。

## web-article-processor

将网页文章处理为包含原文、译文和导读的完整学习资料包。6 步流程：

1. **抓取** — 下载文章内容和图片（调 web-article-saver 的能力）
2. **翻译** — 按照术语规范翻译为中文
3. **校验** — 短文单轮校对，长文三路交叉验证（准确性/流畅度/术语一致性）
4. **分类** — 自动判断文章类型（技术概念/人物故事/实践教程）
5. **导读** — 生成带类比、总览表、思考提示的学习导读
6. **自查** — 8 项质量清单验证

## 输出结构

```
{文章标题}/
├── 英文原文.md              # 或 原文.md（中文文章）
├── 中文翻译.md              # 仅英文文章
├── images/                  # 所有正文引用的图片/视频
│   ├── img-01.jpg
│   └── ...
├── video-01.mp4             # 仅原文含视频时
├── _source-text.md          # 抓取基准（防概括留底）
├── _source-meta.json        # 抓取基准（源正文长度 + 媒体数）
├── {文章标题}-导读.md        # 学习导读（顶层，与原文平级）
└── {文章标题}-校对报告.md    # 翻译质量 QA 报告（仅长文交叉验证时生成）
```

导读放在文章目录**顶层**（不嵌套子目录），文件名带文章标题——在编辑器多标签、全局搜索、跨文章引用场景下都能一眼辨认，且与原文文件名同前缀、排序相邻。

## 安装

### 前置依赖

```bash
# 1. Playwright MCP Server
npm install -g @playwright/mcp@latest

# 2. python3 + curl（脚本工具链）
python3 --version   # 需要 3.8+
curl --version

# 3. ffmpeg（视频下载，无视频需求可跳过）
brew install ffmpeg   # macOS；Linux 用 apt install ffmpeg
```

### 安装 Skills

```bash
git clone https://github.com/matthewliuaw-wq/claude-web-article-skills.git
cd claude-web-article-skills

# 复制到 Claude Code skills 目录
cp -r web-article-saver ~/.claude/skills/
cp -r web-article-processor ~/.claude/skills/
```

### MCP 配置

在项目或用户目录的 `.mcp.json` 中确保配置了 Playwright：

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```

`web_reader` MCP 通常已预装在 Claude Code 环境中。详见 `web-article-saver/references/mcp-setup.md`。

## 使用方法

在 Claude Code 中：

```
# 保存文章（仅抓取，含视频）
帮我下载这篇文章：https://x.com/user/status/12345

# 完整处理（抓取+翻译+导读）
帮我翻译这篇文章：https://mp.weixin.qq.com/s/xxxxx
```

Skills 会根据 URL 自动识别来源并选择对应策略。

## 脚本清单（web-article-saver/scripts/）

| 脚本 | 作用 |
|------|------|
| `download_images.py` | 带 Referer 头批量下载图片（绕过微信防盗链） |
| `extract_x_article.js` | X 长文章 walker（`browser_evaluate` 直接传入，返回正文+内联图位+封面候选） |
| `write_source_meta.py` | 抓取时落基准（源正文长度 + 媒体数） |
| `verify_image_references.py` | 媒体引用双向校验（坏链 + 孤儿媒体） |
| `verify_completeness.py` | 内容完整性校验（翻译对齐 / 正文长度保真 / 媒体数量） |
| `check_all_articles.py` | 批量校验整个知识库目录（`python3 check_all_articles.py <根目录>`） |

## 可选依赖

- **chapter-content-generator** skill：用于生成学习科学增强的导读。若未安装，`web-article-processor` 会根据内置模板生成导读，质量略有降低但流程不受影响。

## Roadmap

- 微信语音（`mp.weixin.qq.com` 音频消息）下载
- 更多来源的类型适配（图片集、转载标记）

## 许可

MIT
