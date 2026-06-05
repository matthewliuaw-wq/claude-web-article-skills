# Claude Code Web Article Skills

两个 Claude Code Skills，用于将网页文章保存、翻译为完整的中文学习资料包。

## web-article-saver

将网页文章完整保存为本地 Markdown + 图片。支持：

- **微信公众号**（mp.weixin.qq.com）— 自动绕过 CDN 防盗链
- **X/Twitter**（x.com）— 滚动加载长推文串
- **普通博客** — 直接抓取

输出结构：
```
{文章标题}/
├── {文章标题}.md
└── images/
    ├── img-01.jpg
    └── ...
```

## web-article-processor

将网页文章处理为包含原文、译文和导读的完整学习资料包。6 步流程：

1. **抓取** — 下载文章内容和图片
2. **翻译** — 按照术语规范翻译为中文
3. **校验** — 短文单轮校对，长文三路交叉验证（准确性/流畅度/术语一致性）
4. **分类** — 自动判断文章类型（技术概念/人物故事/实践教程）
5. **导读** — 生成带类比、总览表、思考提示的学习导读
6. **自查** — 8 项质量清单验证

输出结构：
```
{文章标题}/
├── 英文原文.md
├── 中文翻译.md
├── images/
└── 文章导读/
    ├── 导读.md
    └── 校对报告.md
```

## 安装

### 前置依赖

```bash
# 1. Playwright MCP Server
npm install -g @playwright/mcp@latest

# 2. python3 + curl（图片下载）
python3 --version   # 需要 3.8+
curl --version
```

### 安装 Skills

```bash
# 克隆仓库到 Claude Code skills 目录
git clone https://github.com/YOUR_USERNAME/claude-web-article-skills.git
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

`web_reader` MCP 通常已预装在 Claude Code 环境中。

## 使用方法

在 Claude Code 中：

```
# 保存文章（仅抓取）
帮我下载这篇文章：https://x.com/user/status/12345

# 完整处理（抓取+翻译+导读）
帮我翻译这篇文章：https://mp.weixin.qq.com/s/xxxxx
```

Skills 会根据 URL 自动识别来源并选择对应策略。

## 可选依赖

- **chapter-content-generator** skill：用于生成学习科学增强的导读。若未安装，`web-article-processor` 会根据内置模板生成导读，质量略有降低但流程不受影响。

## 许可

MIT
