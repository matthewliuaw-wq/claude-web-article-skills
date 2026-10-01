# 登录墙 / 反爬源处理（Playwright MCP）

适用：webReader 拿不到正文的源——X 长文章（`x.com/i/article/<id>`）、返回登录页/空正文/反爬拦截的任何站点。

## 铁律：只走 MCP，绝不写 node 脚本

- 手写 node 脚本的 Playwright（`launchPersistentContext`，无论无头/有头/CDP 连真机 Chrome）**会被 X 反爬挡死**——带有效 cookie 也被重定向到 `x.com/i/jf/onboarding?mode=login`。X 对 webdriver/CDP 自动化指纹极敏感。
- **Playwright MCP 的 `browser_*` 工具能通过**——MCP 浏览器指纹不同，X 不拦。
- 结论：这类源只走 MCP 工具，绝不自己写 Playwright 脚本。

## 流程

### 1. browser_navigate(url)

可能**先短暂跳登录墙，别慌**——稍等几秒常常会自动加载出正文（实测 X 长文章导航后先跳 onboarding，随后文章自动渲染）。

### 2. 抓正文——按文章类型分流

**X 长文章 / 多段正文 + 代码块 + 多图 → 首选 `browser_evaluate` 跑 walker 脚本。**

Read [scripts/extract_x_article.js](../scripts/extract_x_article.js) 的整体内容，把它作为 `browser_evaluate` 的 `function` 参数传入。一次返回 `{text, imgs, coverCandidates}`：

- `text`：正文，图片位置已用 `[[IMG1]]..[[IMGn]]` 内联占位，`<pre>` 已包成 ``` 代码围栏 ```
- `imgs`：`[{i, src, w, h}]` 正文内嵌图直链（已去头像/emoji/小图标）
- `coverCandidates`：封面候选——article 级别、在正文容器**之外**的大图（X 长文章封面常在 header，walker 正文里抓不到；取第一个当封面）

**为什么不用 snapshot**：长文 snapshot 是 59KB+ 的 yaml 无障碍树，占用大量上下文且代码块/图位难还原；walker 紧凑十倍、图文位置天然对齐。**长文一律走 walker。**

**短推文 / walker 报错时**：才用 `browser_snapshot`（yaml 无障碍树），适合正文就几句话、没代码块的情况。含视频的推文走视频检测 + HLS 下载（见 [video-download.md](video-download.md)）。

### 3. curl 下载图片

图片直链本身公开（`pbs.twimg.com/media/<id>?format=jpg&name=large`），加浏览器 UA + Referer 即可，**不走登录墙**：

```bash
curl -sL -H "User-Agent: Mozilla/5.0 ..." -H "Referer: https://x.com/" "<img_url>" -o img-02.jpg
```

### 4. 生成 md

长文无需手动找图位锚点——walker 给的 `text` 里 `[[IMGn]]` 占位直接替换成 `![](images/img-0N.ext)`，位置已与原文对齐；封面图（`coverCandidates[0]`）放文章顶部。

## 极罕见情况

连 MCP 都被拦：让用户在**登录态的日常浏览器**里打开文章，复制正文粘贴过来（图片直链仍可单独 curl）。

## 附：无浏览器环境时的替代路径（仅普通推文）

X 普通推文（非长文章）可用 fxtwitter API 抓：`curl https://api.fxtwitter.com/<user>/status/<id>`，返回 Draft.js 正文 + 全部媒体直链。不依赖浏览器、可并行，适合 subagent 无 Playwright 工具时使用。登录墙源（长文章）不适用此法。
