# MCP 环境配置指南

web-article-saver 依赖两个 MCP Server。首次使用前请确认以下配置。

## 1. Playwright MCP Server（必需）

用于打开网页、滚动页面、提取实际加载的图片/视频 URL；**更是登录墙 / 反爬源（如 X 长文章 `x.com/i/article/*`）抓正文的唯一可靠手段**——用 `browser_snapshot` 读正文、`browser_evaluate` 取图。详见 SKILL.md「⭐ 登录墙 / 反爬源」一节。

**安装（推荐，实测有效）：** 用 Claude Code 自带 CLI 注册（user 作用域，所有项目可用）：

```bash
claude mcp add playwright -s user -- npx -y @playwright/mcp@latest
```

> ⚠️ 装完**必须重启 Claude Code**——MCP server 只在启动时加载，本会话装了也不生效。

**验证：** `claude mcp list` 应看到 `playwright ... ✔ Connected`；重启后在会话里有 `browser_navigate` / `browser_snapshot` 等 `browser_*` 工具即可。

**备选（手动配置 .mcp.json）：** 若不用 CLI，在项目根或用户目录的 `.mcp.json` 加：

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp@latest"]
    }
  }
}
```

**重要：登录墙 / 反爬源只能用 MCP 的 `browser_*`，别手写 node 脚本 Playwright。** 实测手写脚本（`launchPersistentContext`，无论无头/有头/CDP 连真机 Chrome）会被 X 反爬挡死；MCP 浏览器指纹不同，能通过。

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
