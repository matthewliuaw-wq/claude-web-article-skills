# Changelog

## v0.2.0（2026-10）

### web-article-saver

- **视频支持（新）**：三类来源完整方案——X/Twitter HLS 分片流（滚动+悬停触发懒加载 → 捕获 master m3u8 → ffmpeg 合流，含失败重试顺序）；微信内嵌视频 mpvideo（渲染后 `<video>` src 即带签名 MP4 直链，时效签名处理）；普通网页直链 mp4
- **登录墙 / 反爬路由（新）**：`web_reader` 拿不到正文时切换 Playwright MCP；收录实战结论「自写 node Playwright 脚本会被 X 反爬挡死、MCP 工具能通过」；新增 X 长文章 walker 脚本 `extract_x_article.js`（`[[IMGn]]` 内联占位，图文位置天然对齐）
- **防概括基准 + 双校验门控（新）**：抓取时落 `_source-text.md` + `_source-meta.json` 基准；收尾强制跑 `verify_image_references.py`（媒体引用双向校验）+ `verify_completeness.py`（翻译结构对齐 / 正文长度保真 / 媒体数量），全绿才算交付
- **图文混排锚点法（新）**：下载时记录每张图的后文锚点，生成 md 时按原文位置嵌入，杜绝「图片堆在文末」
- **脚本扩充**：`download_images.py` 之外新增 5 个（walker / 基准 / 双校验 / 批量校验）；`check_all_articles.py` 支持传入知识库根目录参数
- **文档拆分**：SKILL.md 收敛为流程主干，细节拆至 `references/video-download.md`、`references/anti-crawl.md`、`references/verification.md`
- fxtwitter API 替代路径（无浏览器环境抓普通推文）

### web-article-processor

- **导读位置调整（破坏性变更）**：导读从 `文章导读/` 子目录上移到文章目录**顶层**，命名 `{文章标题}-导读.md`；校对报告同步为 `{文章标题}-校对报告.md`
- 导读内图片引用从 `../images/` 简化为同层 `images/`（与原文一致，消灭一类相对路径错误）

### 工程

- README 重写：核心差异点、新输出结构、脚本清单、Roadmap
- 脚本去除硬编码个人路径

## v0.1.0

- 初始版本：web-article-saver（微信公众号防盗链 + X 滚动加载 + 普通博客，图片下载）、web-article-processor（6 步流水线：抓取→翻译→校验→分类→导读→自查）
