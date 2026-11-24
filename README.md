# 计算机论文索引 · CCF A 2026

按会议、期刊与研究主题浏览 2026 年正式发表的 CCF A 类论文。站点使用静态 HTML、CSS 和 JavaScript，数据随 GitHub 仓库发布。

## 数据覆盖

站点首页显示已收录论文数、来源数与更新时间。各来源的篇数、展示形式和数据源汇总见 [`data/coverage.json`](data/coverage.json)。来源目录包含全部 95 个 CCF A 类会议与期刊，部分来源仍待出版或待核实。

- CCF A 类来源依据 [中国计算机学会第七版正式目录](https://www.ccf.org.cn/Academic_Evaluation/By_category/2026-03-31/870181.shtml)。站内来源目录覆盖 10 个 CCF 领域。目录中的篇数表示本站当前收录量。
- 批量书目来自 [DBLP CC0 快照](https://dblp.org/faq/How%2Bcan%2BI%2Bdownload%2Bthe%2Bwhole%2Bdblp%2Bdataset.html)、[Crossref 出版商书目](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)及大会公开资料，包括 [ICML 论文集](https://proceedings.mlr.press/v306/)、[ICLR 论文目录](https://iclr.cc/virtual/2026/papers.html)、[CVPR 论文集](https://openaccess.thecvf.com/CVPR2026)、[ACL Long Papers](https://aclanthology.org/volumes/2026.acl-long/)和 [JMLR 卷 27](https://jmlr.org/papers/v27/)。
- 期刊按正式卷期年份，会议按正式论文集出版年份收录。对能识别的 Findings、Workshop、短文、海报摘要和演示等作排除。对混合卷册使用卷册名称、页码和已公开的主会类型筛选，个别条目的出版类型仍可能待核对。
- 若同一篇有 Oral 和 Poster，优先展示 Oral。Spotlight、奖项依据公开证据，缺少证据的展示形式标为「未标注」。批量主题优先用官方主题或议程，其余按标题归类，无法归类的条目显示「待细分」。
- 抓取记录保留原文与摘要入口。「有中文笔记」可筛选包含摘要导读和六项阅读笔记的论文。收藏存于当前浏览器。

## 刷新批量书目

需要 Python 3.10 或更新版本和 Node.js 22。在仓库根目录运行以下命令。DBLP 压缩快照约 1 GB，可复用已下载文件。把 `2026-11-24` 替换为当次快照的截止日期。

```sh
python -m pip install requests beautifulsoup4 pymupdf
mkdir .cache
curl --fail --location https://dblp.org/xml/dblp.xml.gz --output .cache/dblp.xml.gz
curl --fail --location https://dblp.org/xml/dblp.dtd --output .cache/dblp.dtd
python scripts/extract-dblp.py .cache/dblp.xml.gz .cache/dblp-2026.json
python scripts/collect-official.py .cache .cache/official-2026.json --refresh
python scripts/collect-publishers.py .cache .cache/publishers-2026.json --date 2026-11-24 --refresh
python scripts/build-corpus.py .cache/dblp-2026.json .cache/official-2026.json --additional .cache/publishers-2026.json --date 2026-11-24
node scripts/validate-data.mjs
```

提交生成的 `data/corpus.json.gz` 与 `data/coverage.json` 即可发布。保留 `data/papers.json` 中的笔记与稳定 ID。

## 增补中文笔记

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

编辑后重跑 `build-corpus.py`，让书目与笔记去重并刷新统计。用 `python -m http.server 8765` 本地启动后访问 [论文索引预览](http://127.0.0.1:8765/)。

## GitHub Pages

将文件置于 `<用户名>.github.io` 仓库，GitHub 仓库 Settings → Pages 中选择 **Deploy from a branch**、`main` 和 `/(root)`。网站也可作为其他 Pages 项目的子目录部署，站内资源使用相对地址。 [GitHub Pages 发布文档](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)

CCF 目录的英文名称、缩写与书目链接参考了 [第七版目录结构化转录](https://github.com/haozhou-wong/ccf-recommended-list-2026-markdown)，并对照 CCF 正式目录 PDF。
