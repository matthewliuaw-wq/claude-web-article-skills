---
name: web-article-processor
description: 将网页文章处理为完整的中文学习资料包。给定一个或多个 URL，自动完成：(1) 抓取文章内容并下载图片，(2) 保存英文原文 Markdown，(3) 翻译为中文，(4) 分级校验（短文单轮校对/长文交叉验证），(5) 调用 chapter-content-generator skill 生成文章导读学习讲义，(6) 导读质量自查。触发场景：用户提供 URL 要求下载文章、翻译网页文章、制作文章导读、处理博客文章。支持并行处理多篇文章。
---

# Web Article Processor

将网页文章（博客、技术文章等）处理为包含原文、译文和导读的完整学习资料包。

## 完整流程（6 步）

### 步骤 1：抓取文章与下载图片

1. 使用 `mcp__web_reader__webReader` 抓取文章内容（Markdown 格式，保留图片）
2. 创建目录结构：
   ```
   {文章标题}/
   ├── images/              # 原文图片
   ├── {文章标题}.md         # 英文原文
   ├── {文章标题}（中文翻译）.md
   └── 文章导读/
       └── {导读标题}.md
   ```
3. 用 `curl -L -o` 下载所有内容图片到 `images/`
4. 将英文内容整理为格式规范的 Markdown，图片引用使用本地路径 `images/xxx.ext`

### 步骤 2：翻译为中文

翻译规则详见 [references/translation-conventions.md](references/translation-conventions.md)。核心要点：

- 保留原文 Markdown 格式结构
- 专有名词保留英文（Claude、Opus、bash、token 等）
- 首次出现的重要术语附英文标注
- 代码不翻译，注释翻译
- 文章开头加 `> 来源信息块`

### 步骤 3：分级校验

根据文章长度选择校验策略：

| 文章长度 | 校验方式 | 说明 |
|:---------|:---------|:-----|
| < 200 行 | 单轮校对 | 1 个 subagent 做全面审校（准确性/流畅度/术语一致性） |
| 200-500 行 | 单轮校对 | 同上，但重点检查漏译 |
| > 500 行 | 交叉验证 | 3 个 subagent 并行审查（准确性/流畅度/术语一致性各一个） |

校验结果保存为 `校对报告.md`，然后根据报告修正译文。

### 步骤 4：判断文章类型

在生成导读前，先判断文章属于哪种类型，决定导读风格：

| 类型 | 特征 | 导读风格 |
|:-----|:-----|:---------|
| A 型：技术概念 | 讲解概念、原理、设计模式 | 类比引入 + "信号→收益"总结 + 数据表对比 |
| B 型：人物故事 | 人物访谈、创业故事、案例 | 叙事性引入 + 时间线 + 金句引用 |
| C 型：实践教程 | 操作指南、工具用法、最佳实践 | 对比引入 + "场景→收益→prompt"格式 |

### 步骤 5：生成导读

**优先使用 `chapter-content-generator` skill**（如已安装）。若未安装，则根据 [references/reading-guide-template.md](references/reading-guide-template.md) 中的模板规范自行生成导读。

使用 chapter-content-generator 时：
1. 用 `Skill` 工具调用 `chapter-content-generator`
2. 传入参数：原始章节内容 = 中文译文，目标 = 生成学习导读
3. 虽然原文不是教材章节，但使用 skill 的学习科学框架来增强导读质量

无论使用哪种方式，导读应遵循以下规范：
- 导读模板和格式详见 [references/reading-guide-template.md](references/reading-guide-template.md)
- 为抽象概念添加日常经验类比
- 用表格对比不同方案/方法的优劣
- 用 ASCII 可视化复杂流程
- 导读保存到 `文章导读/` 子目录，图片使用 `../images/` 相对路径

### 步骤 6：导读质量自查

导读生成后，执行以下自查：

- [ ] 开篇有类比或引人入胜的引入
- [ ] 有总览表/全局图
- [ ] 原文图片全部保留且路径正确
- [ ] 至少 2 处思考提示框
- [ ] 结尾有拓展思考问题
- [ ] 中文表达自然流畅
- [ ] 文章类型适配正确（A/B/C 型）

如发现问题，直接修正。

## 并行处理多篇

当用户一次提供多个 URL 时：

1. 先并行抓取所有文章内容
2. 为每篇文章启动独立的 subagent（使用 `Agent` 工具，`run_in_background: true`）
3. 每个 subagent 独立完成步骤 1-6
4. 全部完成后汇总结果

## 可选依赖

- **chapter-content-generator** skill：用于生成学习科学增强的导读（步骤 5）。若未安装，skill 会根据 `references/reading-guide-template.md` 中的模板规范自行生成导读，质量略有降低但流程不受影响。
