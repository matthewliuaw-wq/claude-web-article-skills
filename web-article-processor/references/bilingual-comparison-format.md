# 中英对照文档格式规范

## 文档结构

对照文档由以下部分组成：

1. **来源信息头** — 文章元信息
2. **逐段对照正文** — 英文原文段落 + 中文译文引用块
3. **（可选）术语对照附录** — 关键术语汇总

## 格式规范

### 来源信息头

```markdown
> **原文**：[文章标题](URL) · 作者 · 发布日期
> **模式**：中英逐段对照

---
```

### 普通段落对照

英文段落保持原样，紧跟一个引用块放中文翻译：

```markdown
This is the first paragraph of the original English article. It contains
several sentences that convey the main idea of the section.

> **译文**：这是原始英文文章的第一段。它包含若干句子，传达了本节的核心思想。

This is the second paragraph with more details.

> **译文**：第二段包含更多细节。
```

### 标题

章节标题保持英文原文，不翻译：

```markdown
## Getting Started with Agents

正文段落...

> **译文**：正文翻译...
```

### 代码块

代码块不翻译，只出现一次。代码后的注释说明可翻译：

```markdown
```python
# Create an agent with tools
agent = Agent(model="claude-sonnet-4-6", tools=[search, calculator])
result = agent.run("What is 2+2?")
```

> **译文**：上面的代码创建了一个带有工具的智能体（agent），并运行了一个简单的查询。
```

### 图片

图片只在英文段落后出现一次，译文引用块中不重复图片：

```markdown
The architecture diagram shows the overall system design:

![Architecture Diagram](images/architecture.png)

> **译文**：架构图展示了系统的整体设计。
```

### 表格

先放英文原表，再放中文翻译表：

```markdown
| Model | Context Window | Speed |
|-------|---------------|-------|
| Opus  | 200K          | Slow  |
| Sonnet| 200K          | Fast  |

> **译文**：

| 模型 | 上下文窗口 | 速度 |
|------|-----------|------|
| Opus | 200K      | 慢   |
| Sonnet | 200K    | 快   |
```

### 列表

列表项逐条对照：

```markdown
Key benefits include:
- **Speed**: 10x faster inference
- **Cost**: 50% reduction in token usage
- **Quality**: Improved accuracy on benchmarks

> **译文**：核心优势包括：
> - **速度**：推理速度提升 10 倍
> - **成本**：token 使用量减少 50%
> - **质量**：基准测试准确率提升
```

### 章节分隔

章节之间用分隔线隔开：

```markdown
---

## Next Section

Content continues...
```

## 禁止事项

- ❌ 不要将标题翻译为中文（保持英文原标题便于对照）
- ❌ 不要在译文中重复代码块
- ❌ 不要在译文中重复图片
- ❌ 不要省略任何段落（必须逐段完整对照）
- ❌ 不要改变原文的 Markdown 结构（标题层级、列表缩进等）

## 质量检查清单

- [ ] 每个英文段落都有对应的 `> **译文**：` 引用块
- [ ] 没有遗漏的段落
- [ ] 代码块只出现一次
- [ ] 图片只出现一次
- [ ] 表格有英文原表 + 中文翻译表
- [ ] 标题保持英文原文
- [ ] 来源信息头完整（标题、URL、作者、日期）
- [ ] 章节之间有分隔线
- [ ] 术语翻译全文一致
