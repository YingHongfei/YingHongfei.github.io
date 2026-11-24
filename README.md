# 计算机论文索引 · CCF A 2026

按会议、期刊与研究主题浏览 2026 年正式发表的 CCF A 类论文。站点使用静态 HTML、CSS 和 JavaScript，数据随 GitHub 仓库发布。

## 收录口径

- CCF A 类来源依据 [中国计算机学会第七版正式目录](https://www.ccf.org.cn/Academic_Evaluation/By_category/2026-03-31/870181.shtml)。站内来源目录覆盖 10 个 CCF 领域。目录中的篇数表示本站当前收录量。
- 论文库当前为精选收录。会议论文按正式主会论文集发表年份纳入，期刊论文按正式出版年份纳入。早于 2026 年正式出版、后来在 2026 年会议报告的论文不计入。
- 展示标签依据大会公开议程或官方录用记录。若同一篇有 Oral 和 Poster，以 Oral 展示。Spotlight 和奖项分别依据大会公告，无法核实的展示形式标为「未标注」。
- 主题目录、中文摘要导读和六项阅读笔记由本站整理。完整原文摘要、展示与获奖信息可从论文卡片上的链接核对。收藏存于当前浏览器。

## 新增论文

在 [`data/papers.json`](data/papers.json) 增加一个条目，沿用现有结构。

| 字段 | 内容 |
| --- | --- |
| `id`、`venue`、`year` | 唯一 ID、[`data/venues.json`](data/venues.json) 中的来源 ID、正式发表年份 `2026` |
| `title`、`authors`、`source` | 论文标题、按发表顺序排列的完整作者列表、可查看原文摘要的正式页面 |
| `topics`、`keywords` | `topics` 是一个或多个由宽到窄的路径，例如 `[["机器学习", "智能体", "多智能体系统"]]`。`keywords` 用于中英文检索 |
| `format`、`formatSource` | `oral`、`spotlight`、`poster`、`journal` 或 `unknown`。前三种需填写公开证据链接 |
| `award` | 有奖项时填写 `label` 和 `source` |
| `notes`、`abstractZh` | 动机、问题、现象、方法、实验、贡献六项中文笔记，以及摘要导读 |
| `links` | 补充入口数组，例如论文 PDF、OpenReview、代码或 DOI |

运行 `node scripts/validate-data.mjs` 检查年份、来源、去重、主题、链接和必填字段。用 `python -m http.server 8765` 本地启动后访问 [论文索引预览](http://127.0.0.1:8765/)。

## GitHub Pages

将文件置于 `<用户名>.github.io` 仓库，GitHub 仓库 Settings → Pages 中选择 **Deploy from a branch**、`main` 和 `/(root)`。网站也可作为其他 Pages 项目的子目录部署，站内资源使用相对地址。 [GitHub Pages 发布文档](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)

CCF 目录的英文名称、缩写与书目链接参考了 [第七版目录结构化转录](https://github.com/haozhou-wong/ccf-recommended-list-2026-markdown)，并对照 CCF 正式目录 PDF。
