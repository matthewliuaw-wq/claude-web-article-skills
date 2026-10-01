---
name: web-article-processor
description: 将网页文章处理为完整的中文学习资料包。给定一个或多个 URL，自动完成：(1) 抓取文章内容并下载图片，(2) 保存英文原文 Markdown，(3) 翻译为中文，(4) 分级校验（短文单轮校对/长文交叉验证），(5) 调用 chapter-content-generator skill 生成文章导读学习讲义，(6) 导读质量自查。触发场景：用户提供 URL 要求下载文章、翻译网页文章、制作文章导读、处理博客文章。支持并行处理多篇文章。也支持"中英对照"输出模式，生成逐段双语对照文档。
---

# Web Article Processor

将网页文章（博客、技术文章等）处理为包含原文、译文和导读的完整学习资料包。

## ⚠️ 权限友好写法（避免触发确认 / background subagent 卡死）

Claude Code 的 Bash 权限白名单按**命令开头**匹配（`Bash(curl:*)` 匹配以 curl 开头的命令）。**含 shell 关键字的复合命令匹配不了**，会触发确认——在 background subagent 里会**直接卡死**（不能交互确认）。务必遵守：

- ✅ **绝对路径，不要 `cd dir && cmd`**：`curl -o <绝对路径>/images/cover.jpg ...`、`python3 /abs/path/script.py`
- ✅ **多个下载 = 一条消息发多个独立 `curl` 调用**（harness 并行），不要 `for u in ...; do curl; done`
- ✅ **复杂逻辑写成 python 脚本**（单 `python3 script.py` 调用），不要 bash `for`/`heredoc`（`python3 << EOF`）/`declare -A`
- ❌ 避免：`for`/`while`/`if`、`declare`、`heredoc`、`&&`/`;`/`|` 串联多命令

**核心：一条 bash 只做一件事，开头是简单命令。** 多步操作拆成多条单命令，或写成 python 脚本一次跑。批量校验用 `web-article-saver` 的 `check_all_articles.py <知识库根目录>`。

## 输出模式

用户可通过提示词选择输出模式，默认为模式 B。

| 模式 | 名称 | 触发信号 | 输出 |
|:----:|:----:|:---------|:-----|
| **A** | 仅存档 | "只保存"、"不翻译"、"存档" | 英文原文 + 图片 |
| **B** | 完整资料包 | "翻译"、"导读"、"处理文章"（默认） | 原文 + 译文 + 导读 |
| **C** | 中英对照 | "对照"、"双语"、"中英对照"、"bilingual" | 逐段双语对照文档 + 图片 |

## 输出位置（工作目录自适应）

文章统一归集到名为「网页文章」的目录下，按当前工作目录（cwd）自适应定位：

1. **若 cwd 本身就叫「网页文章」**（例 `~/Documents/网页文章/`）→ 直接把文章存到 cwd 下。
2. **否则** → 在 cwd 下查找名为「网页文章」的子目录：已存在就存进去；不存在就在 cwd 下新建 `网页文章/` 再存。

判定命令：

```bash
[ "$(basename "$PWD")" = "网页文章" ] && echo "$PWD" || echo "$PWD/网页文章"
```

下方各模式的 `{文章标题}/` 都位于这里确定的「网页文章」输出位置之下。无论从哪个项目调用本 skill，文章都会就近归集到「网页文章」，不散落各处。

### 各模式输出目录结构

**模式 A（仅存档）：**
```
{文章标题}/
├── images/
│   └── ...
└── {文章标题}.md              # 英文原文
```

**模式 B（完整资料包）：**
```
{文章标题}/
├── images/
│   └── ...
├── {文章标题}.md              # 英文原文
├── {文章标题}（中文翻译）.md    # 中文译文
└── {文章标题}-导读.md          # 学习导读（顶层，与原文平级）
```

**模式 C（中英对照）：**
```
{文章标题}/
├── images/
│   └── ...
└── {文章标题}（中英对照）.md    # 逐段双语对照
```

## 完整流程

### 步骤 1：抓取文章与下载图片（所有模式共用）

**抓取方法（按来源选，web_reader 配额耗尽时的 fallback 链）**:

- 默认 `mcp__web_reader__webReader`（Markdown 格式）。**web_reader 配额常耗尽（月度上限）**,失败时按来源 fallback：
- **X 文章**(`x.com/<user>/status/<id>`):用 **fxtwitter API**——`curl 'https://api.fxtwitter.com/<user>/status/<id>'` 返回 JSON(Draft.js 正文 + 全部媒体直链)。自写 Draft.js→Markdown 解析(遍历 blocks,atomic→`[[IMGn]]` 占位;注意 entityMap 里 MARKDOWN 类型 entity 会让 media_entities 索引错位,跑完 verify 有孤儿要手动补插)。不依赖浏览器、可多 curl 并行。
- **微信公众号**(`mp.weixin.qq.com/s/<id>`):用 **curl 直抓 SSR HTML**——`curl -sL -H 'User-Agent: ...' '<url>'` 返回完整 HTML(`#js_content` 正文 + 所有 `<img data-src>`,SSR 全渲染**无懒加载**,比 Playwright walker 还稳)。自写 HTML→Markdown 解析。图片带 `Referer: https://mp.weixin.qq.com/` 下,去 `tp=webp` 拿原图。
- **登录墙/反爬源**:用 Playwright MCP(`browser_navigate` + `browser_evaluate` walker;见 saver skill「⭐ 登录墙」节)。

> 🟢 **抓取后立即「落基准」(防静默概括,必做)**:把抓取返回的**原始未加工正文**原样存为 `<文章目录>/_source-text.md`,再跑:
> ```bash
> python3 ~/.claude/skills/web-article-saver/scripts/write_source_meta.py "<文章目录>" \
>   --url "文章URL" --method webReader --videos <video数> --imgs <图片数>
> ```
> 抓取瞬间锁定源正文长度 + 媒体数。无它,译文/正文若被悄悄概括,永远查不出。详见 saver 第一步。

1. 使用 `mcp__web_reader__webReader` 抓取文章内容（Markdown 格式，保留图片）
2. 用 `curl -L -o` 下载所有内容图片到 `images/`
3. 将英文内容整理为格式规范的 Markdown，图片引用使用本地路径 `images/xxx.ext`
4. **⚠️ 图片必须按原文精确位置嵌入正文（关键铁律）**——不要只下载不嵌，也不要堆在文末。正确做法详见 `web-article-saver` skill 第四步：用 Playwright 遍历每张 `<img>`，取它**后面紧跟的第一段正文**作为"后文锚点"，生成 md 时按锚点把 `![图N](images/0N.ext)` 插到对应段落之前（图在段落上方）。**生成原文 md 后，立即运行校验脚本做双向核对**：

```bash
python3 ~/.claude/skills/web-article-saver/scripts/verify_image_references.py "<文章目录>"
```

脚本必须输出 `✅ 全部正常`（退出码 0）才算通过。它比"自数引用数"更可靠——能抓出"图片下好了却没插进 md"这种最常犯的错（孤儿媒体）。报告孤儿媒体 = 漏插，回锚点法补插后重跑。
5. **如果原文含视频**（X/Twitter 推文常见）：参照 `web-article-saver` skill 的视频下载流程——用 Playwright 检测 `<video>` 元素（提取 `poster` 里的视频 ID）→ 滚动到每个视频位置触发懒加载 → 从 network 请求取 master m3u8 → `ffmpeg -c copy -bsf:a aac_adtstoasc` 下载为 `video-01.mp4` 等。在原文 Markdown 对应位置插入 `<video controls width="100%" src="images/video-XX.mp4"></video>`；翻译/对照文档中 **保留 video 标签不翻译**
6. **如果是模式 A**：保存英文原文后结束，不执行后续步骤

### 步骤 2：翻译为中文（模式 B/C 共用）

翻译规则详见 [references/translation-conventions.md](references/translation-conventions.md)。核心要点：

- 保留原文 Markdown 格式结构
- 专有名词保留英文（Claude、Opus、bash、token 等）
- 首次出现的重要术语附英文标注
- 代码不翻译，注释翻译
- 文章开头加 `> 来源信息块`
- **⚠️ 图片/视频必须同步带入译文**：译文要保留原文里所有 `![图N](images/0N.ext)` 和 `<video>` 引用，并嵌在对应的**中文段落**位置（不是英文段落）。做法：翻译时记住每张图原本在哪段英文前，译文把该段翻成中文后，图片就插在那段中文之前。**译文生成后再跑一次 `verify_image_references.py`**：译文 md 引用的图片数必须 == 原文，且无孤儿、无坏链。中英对照（模式 C）合并后还要再跑一次——合并是漏图重灾区。

- **⚠️ 译文完整性校验（必跑 `verify_completeness.py`）**：翻译时可能静默漏段/漏图/被概括,`verify_image_references.py` 查不出这类。译文生成后跑:
  ```bash
  python3 ~/.claude/skills/web-article-saver/scripts/verify_completeness.py "<文章目录>"
  ```
  对比英文原文 vs 中文翻译的段落/图片/列表项,**中文比英文少超阈值**即告警(漏段/漏图/概括;单向,中文多为翻译增值不报)。退出码非 0 必须回译步骤补全后重跑。

**如果是模式 B**：翻译结果独立保存为 `{文章标题}（中文翻译）.md`

**如果是模式 C**：翻译结果暂存，进入步骤 2C 生成对照文档

### 步骤 2C：生成中英对照文档（仅模式 C）

将原文和译文逐段合并为一个双语对照 Markdown 文件。格式规范详见 [references/bilingual-comparison-format.md](references/bilingual-comparison-format.md)。

**核心格式**：
```markdown
> **原文**：[文章标题](URL) · 作者 · 日期

---

## Section Title

English paragraph here. This is the original text from the article.

> **译文**：中文翻译内容放在引用块中，与英文段落一一对应。

---

## Another Section

More English text...

> **译文**：更多中文翻译...
```

**关键规则**：
- 每个自然段/小节，英文原文在前，中文译文紧跟其后放在 `> **译文**：` 引用块中
- 标题保持英文原文（不翻译），翻译内容只在段落级对照
- 代码块不翻译，在对照文档中只出现一次
- 图片只在英文段落后出现一次，引用块中不重复
- 表格类内容：先英文原表，后中文翻译表，中间用 `> **译文**：` 标记
- 分隔线 `---` 用于章节之间

对照文档保存为 `{文章标题}（中英对照）.md`。

**⚠️ 模式 C 收尾必跑校验**：中英对照合并时极易整张图丢失（合并逻辑只记得"图只出现一次"，容易把某张图彻底漏掉）。保存后**必须**运行：

```bash
python3 ~/.claude/skills/web-article-saver/scripts/verify_image_references.py "<文章目录>"
```

对照文档 md 引用的图片数必须 == `images/` 文件数，无孤儿媒体。实战中曾出现 8 张图只插了 7 张、第 8 张孤儿躺着的 bug——正是靠这个脚本抓出来的。报告孤儿必须补插重跑。

### 步骤 3：分级校验（模式 B/C 共用）

根据文章长度选择校验策略：

| 文章长度 | 校验方式 | 说明 |
|:---------|:---------|:-----|
| < 200 行 | 单轮校对 | 1 个 subagent 做全面审校（准确性/流畅度/术语一致性） |
| 200-500 行 | 单轮校对 | 同上，但重点检查漏译 |
| > 500 行 | 交叉验证 | 3 个 subagent 并行审查（准确性/流畅度/术语一致性各一个） |

**模式 B**：校验结果保存为 `校对报告.md`，然后根据报告修正译文。

**模式 C**：校验针对对照文档中的译文部分，检查中英对照的对应关系是否完整、是否有遗漏段落。修正后更新对照文档。

### 步骤 4-6：生成导读（仅模式 B）

**如果是模式 C**：步骤 3 校验完成后即结束，不生成导读。

**如果是模式 B**：继续执行步骤 4-6。

#### 步骤 4：判断文章类型

在生成导读前，先判断文章属于哪种类型，决定导读风格：

| 类型 | 特征 | 导读风格 |
|:-----|:-----|:---------|
| A 型：技术概念 | 讲解概念、原理、设计模式 | 类比引入 + "信号→收益"总结 + 数据表对比 |
| B 型：人物故事 | 人物访谈、创业故事、案例 | 叙事性引入 + 时间线 + 金句引用 |
| C 型：实践教程 | 操作指南、工具用法、最佳实践 | 对比引入 + "场景→收益→prompt"格式 |

#### 步骤 5：调用 chapter-content-generator 生成导读

**这一步必须正式调用 `chapter-content-generator` skill**，而非简单仿写。

具体做法：
1. 用 `Skill` 工具调用 `chapter-content-generator`
2. 传入参数：原始章节内容 = 中文译文，目标 = 生成学习导读
3. 虽然原文不是教材章节，但使用 skill 的学习科学框架来增强导读质量：
   - T1 类比设计模板：为抽象概念添加日常经验类比
   - T2 概念对比表：对比不同方案/方法的优劣
   - T9 操作流程图：用 ASCII 可视化复杂流程
4. 导读模板和格式规范详见 [references/reading-guide-template.md](references/reading-guide-template.md)
5. **图片保留**：导读里凡是要解读的原文图示/截图，都要用 `![图N](images/0N.ext)` 嵌进来，不要只用文字描述"见原文图"。读者打开导读就能看到图。

导读保存到文章目录顶层，命名 `{文章标题}-导读.md`（与原文平级、排序相邻），图片用同层 `images/` 相对路径。

#### 步骤 6：导读质量自查

导读生成后，执行以下自查：

- [ ] 开篇有类比或引人入胜的引入
- [ ] 有总览表/全局图
- [ ] 原文图片全部保留且路径正确（可直接跑 `verify_image_references.py` 复核，无孤儿即通过）
- [ ] 至少 2 处思考提示框
- [ ] 结尾有拓展思考问题
- [ ] 中文表达自然流畅
- [ ] 文章类型适配正确（A/B/C 型）

如发现问题，直接修正。

## 批量处理多篇（小批量串行，避免 API 中断 / 权限卡死）

当用户一次提供多个 URL（如跑 inbox）时：

1. **分批:每批 3-5 篇**（一个 subagent 处理一批）。**不要 9+ 篇/批**——长翻译累积会触发 API「Connection closed mid-response」中断（实测过 9 篇/批两次都断在翻译环节）。
2. **一次只启动 1 个 subagent**（background），等它完成通知再启动下一批。**不要同时启动多个处理同样/重叠 URL 的 subagent**（会互相 SendMessage 干扰、写同名目录冲突）。
3. **subagent 自己串行处理批内每篇**（一篇全做完——抓取→落基准→翻译/导读→双校验——再做下一篇），**不要 fork 子 agent**（fork 出来的子 agent 成为 orphan，管理混乱、难追踪）。
4. 每个 subagent 的 prompt 里明确：互斥 URL 列表 + 抓取方法（X 用 fxtwitter / 公众号用 curl SSR / 登录墙用 Playwright）+ 提醒遵守本 skill 顶部「权限友好写法」。
5. 全部批次完成后，主会话用 `python3 ~/.claude/skills/web-article-saver/scripts/check_all_articles.py [前缀]` 一次性诊断全部。

**为什么串行不并行**：X 用 fxtwitter（不占 Playwright）理论上可并行，但多 subagent 同时跑会互相发消息确认目录归属、写同名目录冲突，管理成本远大于串行等待。Playwright（公众号/登录墙）是单浏览器，必须串行。

## 与现有项目的关系

本 skill 处理的输出文件按上方「输出位置（工作目录自适应）」的规则归集——cwd 叫「网页文章」就存 cwd，否则存 cwd 下的 `网页文章/`。这与 CLAUDE.md 中定义的 PDF 翻译工作流（`资料翻译/`）是平行的两套流程。

- PDF 报告翻译 → `资料翻译/` 目录（使用 `pdf-report-translator` skill）
- 网页文章处理 → `网页文章/` 目录（使用本 skill，位置自适应）
