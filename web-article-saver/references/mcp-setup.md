# MCP 环境配置指南

web-article-saver 依赖两个 MCP Server。首次使用前请确认以下配置。

## 1. Playwright MCP Server（必需）

用于打开网页、滚动页面、提取实际加载的图片 URL。

**安装：**

```bash
npm install -g @playwright/mcp@latest
```

**配置：** 在项目根目录或用户目录的 `.mcp.json` 中添加：

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

**验证：** 在 CC 中输入任何涉及浏览器的操作，如果出现 `browser_navigate`、`browser_snapshot` 等工具提示，说明配置成功。

## 2. web_reader MCP Server（必需）

用于抓取网页全文内容。

此工具通常已预装在 Claude Code 环境中。如果不可用，会显示为 `mcp__web_reader__webReader`。

**验证：** 让 CC 执行 `webReader(url="https://example.com")`，如果返回网页内容则正常。

## 3. python3 + curl（必需）

图片下载脚本 `scripts/download_images.py` 依赖 python3 和 curl。

**验证：**

```bash
python3 --version   # 需要 3.8+
curl --version      # 任意版本
```

## 快速检查清单

让 CC 执行以下命令一次性验证所有依赖：

```
请检查 web-article-saver skill 的依赖环境：
1. 检查 Playwright MCP 是否可用（尝试 browser_snapshot）
2. 检查 web_reader MCP 是否可用
3. 检查 python3 和 curl 是否存在
4. 报告哪些已就绪、哪些需要安装
```
