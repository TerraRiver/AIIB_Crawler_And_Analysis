# 01 常规项目模块 (`projects`) 数据采集说明大纲

## 一、数据源与采集方式

### 1.1 官网原始数据接口与页面
- **全部常规项目列表数据文件**
  - 前端展示页面：`https://www.aiib.org/en/projects/list/index.html`（顶部菜单 `WHAT WE DO` -> `PROJECTS` -> `Project List`）
  - 后台数据接口：`https://www.aiib.org/en/projects/list/.content/all-projects-data.js`
  - 数据格式：JavaScript 变量赋值文本（`var data = [...]`），内部为 JSON 数组。
  - 覆盖范围：亚投行官网公开的全部常规项目列表记录（共 501 条，含已批准、拟议中、已取消/终止项目）。
- **单个项目详情页面**
  - 页面地址格式：`https://www.aiib.org` + 项目列表中的 `path` 字段（如 `/en/projects/details/2021/approved/India-Punjab-Municipal-Services-Improvement-Project.html`）。
  - 数据格式：静态 HTML 页面。
  - 页面包含的三个数据区块：
    1. 顶部信息栏（CSS 选择器 `.summary-item`）：记录项目编号、状态、国家、行业、环社类别、融资金额、融资类型、概念审查日期、批准日期、最近现场访问日期、贷款关闭日期。
    2. 正文段落区（CSS 选择器 `.project-paragraph .paragraph`）：记录项目目标、项目描述、环境与社会信息、项目团队负责人、借款人、执行机构。
    3. 页面底部文档列表（CSS 选择器 `.feature-documents .doc`）：记录该项目披露的各类 PDF 文档标题、发布日期与下载链接。

### 1.2 采集与落盘流程
- **步骤 1**：通过 HTTP GET 请求拉取 `all-projects-data.js`，剥离外层 JavaScript 变量声明后解析为 JSON 数组，并对金额、年份、相对路径 URL 做格式转换。
- **步骤 2**：从全部项目列表中筛选出 `economy` 为 `India` 的记录（共 72 条），作为本次详情页采集对象（也可通过命令行参数 `--country ALL` 切换为采集全行所有项目的详情页）。
- **步骤 3**：按序请求每个项目的详情页 HTML，提取顶部信息栏、正文段落区、底部文档链接，并在解析过程中根据文本内容提取辅助字段（审批间隔天数、联合融资机构名称、涉及的印度邦名等）。
- **步骤 4**：每采集一条详情页记录，先写入增量日志文件 `.journal.jsonl` 并记录到 `state.json`，每满 10 条及模块结束时合并写入最终 JSON 文件。
- **步骤 5**：当配置参数 `--download-pdfs` 设为 `india` 或 `all` 时，遍历详情页中的 PDF 链接，将文件下载至 `data/projects/pdfs/<项目编号_国家>/` 目录。

### 1.3 采集命令与参数说明

```bash
# 1. 采集全行 501 条项目主表 + 印度 72 条项目详情页（不下载 PDF 附件）
uv run python main.py --types projects --country India --download-pdfs none --mode resume

# 2. 采集全行 501 条项目主表 + 印度 72 条项目详情页 + 下载印度项目关联的全部 PDF 文件
uv run python main.py --types projects --country India --download-pdfs india --mode resume

# 3. 采集全行全部 501 个项目的详情页（优先采集印度，再采集其余国家）
uv run python main.py --types projects --country ALL --download-pdfs none --mode resume

# 4. 备份已有数据并重新采集项目模块（可附加年份范围与最大详情页数量限制）
uv run python main.py --types projects --country India --since 2016 --until 2026 --max-detail-pages 0 --mode reset
```

- `--types projects`：指定仅运行常规项目模块。
- `--country`：控制详情页采集范围；设为 `India` 时仅请求印度项目的详情页，设为 `ALL` 时请求全行所有项目的详情页（主表 `all_projects_summary.json` 始终保存全行 501 条记录）。
- `--download-pdfs`：控制详情页内 PDF 链接的下载范围，可选 `none`（不下载）、`india`（仅下载印度项目 PDF）、`all`（下载所有已采集详情页项目的 PDF）。
- `--max-detail-pages`：限制最多采集的详情页数量，`0` 表示不限制。
- `--since` / `--until`：按项目批准年份（`approval_year`）过滤采集范围。
- `--mode`：断点模式，`resume` 表示跳过已在 `data/state.json` 中记录的详情页 URL 和附件，`reset` 表示将旧数据移入 `data/backups/<时间戳>/` 后重新采集。

---

## 二、本地输出文件清单

| 文件路径 | 对应数据源 | 内容说明 | 当前记录条数 |
| :--- | :--- | :--- | :--- |
| `data/projects/all_projects_summary.json` | `all-projects-data.js` | 全行所有常规项目的列表信息 | 501 条 |
| `data/projects/india_projects_summary.json` | `all-projects-data.js` | 从全行常规项目列表中筛选出的印度项目列表信息 | 72 条 |
| `data/projects/india_project_details.json` | 各印度项目详情页 HTML | 印度全部常规项目的详情页解析结果 | 72 条 |
| `data/projects/project_details_all.json` | 已采集的项目详情页 HTML | 本次运行累计采集的所有常规项目详情页记录 | 72 条 |
| `data/projects.json` | 同 `project_details_all.json` | 模块主汇总文件 | 72 条 |

---

## 三、数据表字段说明

### 3.1 项目列表文件字段 (`all_projects_summary.json` / `india_projects_summary.json`)
- 逐一列出 18 个字段的名称、数据类型、数据来源（原始字段名）及转换规则：
  - `record_id`、`approval_year`、`date_raw`、`economy`、`sector`、`financing_type`、`project_type`、`name`、`status`、`approved_funding_raw`、`approved_funding_usd_millions`、`committed_funding_raw`、`proposed_funding_raw`、`proposed_funding_usd_millions`、`effective_funding_usd_millions`、`special_funding_raw`、`detail_path`、`detail_url`。

### 3.2 项目详情页文件字段 (`india_project_details.json` / `project_details_all.json`)
分为四组说明每个字段的名称、类型、页面提取位置与处理规则：
- **第 1 组：页面顶部信息栏字段（`.summary-item`）**
  - `project_number`、`status`、`economy`、`sector`、`es_category`、`financing_type`、`approved_funding_raw`、`approved_funding_usd_millions`、`proposed_funding_raw`、`proposed_funding_usd_millions`、`concept_review_date`、`financing_approval_date`、`latest_field_visit`、`loan_closing_date`、`raw_summary_fields`。
- **第 2 组：页面正文段落字段（`.project-paragraph .paragraph`）**
  - `title`、`objective`、`description`、`environmental_and_social_info`、`project_team_leader`、`borrower`、`implementing_entity`。
- **第 3 组：页面底部文档列表字段（`.feature-documents .doc`）**
  - `documents_count`、`pimr_count`、`documents`（数组内每个对象的 `category`、`title`、`date`、`url`、`doc_type`、`local_path`）。
- **第 4 组：解析时生成的计算与规则匹配字段**
  - `approval_lag_days`：由 `financing_approval_date` 减去 `concept_review_date` 计算出的天数（若任一日期缺失则为 `null`）。
  - `is_cofinanced` 与 `cofinanciers`：通过正则表达式在文本中匹配世行、亚行等机构名称的结果。
  - `applicable_es_policy`：根据环社信息段落中是否声明适用联合融资机构政策生成的标识。
  - `is_fi_onlending`：根据 `es_category` 是否为 `FI` 或正文中是否包含转贷关键词生成的布尔值。
  - `indian_states`：根据印度地名映射表在项目文本中匹配出的邦或联邦属地名称列表。
  - `list_project_type`、`list_approval_year`、`list_effective_funding_usd_millions`：从列表页合并过来的对应字段。

---

## 四、数据缺失情况与已知边界
- 说明详情页部分字段在官网原始页面中即为空值或未披露的情况（例如拟议中或早期取消的项目无 `financing_approval_date`，部分非主权项目不披露 `latest_field_visit` 或 `loan_closing_date`）。
- 说明文本规则匹配字段（如 `cofinanciers`、`indian_states`）的匹配词表范围与局限。
