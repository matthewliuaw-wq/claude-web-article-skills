# 翻译规则与术语约定

## 通用规则

1. **保留原文 Markdown 格式结构**（标题层级、列表、表格、代码块）
2. **代码块内代码不翻译**，注释翻译为中文
3. **文章开头加来源信息块**：
   ```markdown
   > **原文**：[标题](URL) · 发布日期 · 作者
   > **导读目标**：用 X 分钟读懂本文的核心思想。
   ```
4. **首次出现的重要术语附英文标注**，如"子智能体（subagent）"
5. **图片路径**：原文在 `images/`，导读在 `文章导读/` 中用 `../images/`

## 术语处理

### 保留英文的专有名词
- 产品名：Claude、Claude Code、Claude.ai、Claude Design
- 模型名：Opus、Sonnet、Haiku（带版本号如 Opus 4.6）
- 技术名：bash、token、REPL、HTML、CSS、SVG、JavaScript、TypeScript、React、Swift
- 公司名：Anthropic、Apple、Google、Meta、Linear、Slack、Sentry、Amplitude
- 基准测试：SWE-bench、BrowseComp
- 配置文件：CLAUDE.md、SKILL.md、YAML frontmatter

### 统一翻译的术语

| 英文 | 中文 | 备注 |
|:-----|:-----|:-----|
| agent | 智能体 | |
| subagent | 子智能体 | |
| agent harness | 智能体框架 | |
| context window | 上下文窗口 | |
| tool calling | 工具调用 | |
| compaction | 压缩 | 指上下文压缩 |
| cache hits | 缓存命中 | |
| prompt | 提示词 | 作名词时 |
| skill | 技能 | |
| hook | 钩子 | |

## 翻译质量标准

- 无漏译（所有段落都要覆盖）
- 无误译（技术描述准确）
- 无翻译腔（读起来像中文原创文章）
- 术语全文一致（同一术语始终使用相同翻译）
