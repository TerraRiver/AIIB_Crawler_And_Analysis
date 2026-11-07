# 02 项目采购模块 (`procurement`) 数据采集说明大纲

## 一、数据内容与数据源说明

### 1.1 数据业务含义与构成
常规项目模块（`projects`）记录的是“亚投行把钱批给了哪个项目”，而项目采购模块（`procurement`）记录的是**“项目拿到钱之后，通过招标把具体的工程、设备或咨询服务包给了哪家企业、签了多少钱的合同”**。

亚投行批出一笔基础设施贷款后，当地执行机构必须按亚投行的采购规定，把工程拆分成具体的施工、设备采购或工程咨询标段，走公开招投标流程。官网将该招投标流程产生的公开记录放在 `Project Procurement Opportunities` 栏目下，核心由以下三部分组成：

1. **采购列表页（`ppo-data-all.js`，共 1,189 条记录）**
   按时间倒序记录各个项目在招投标三个阶段发布的日常公告（对应数据中的 `category` 字段）：
   - **采购计划（`Procurement Plan`）**：项目启动时公布的清单，说明该项目接下来准备招哪些标段。
   - **招标公告（`Notices`）**：对外发布的招标通知，说明某个工程标段开始招投标及投标截止日期。
   - **中标合同通知（`Contract Awards`，共 292 条，其中涉印记录 42 条）**：招投标结束后发布的近期单条中标通知（主要集中在 2024–2026 年），并附带每份通知对应的 PDF 下载链接。
     - **样本实例 1（阿萨姆邦电网升级二期项目）**：标段为“修建 Morigaon 220/132KV 变电站及配套输电线”，中标企业为印度 `M/s Lumino Industries Ltd. (Kolkata, West Bengal)` 与 `M/s AK Das associated Ltd (Bhubaneswar, Odisha)`，签约日期 `Aug. 21, 2026`，合同金额 `INR 2,078,489,885.00`（约 20.78 亿印度卢比）。
     - **样本实例 2（科钦地铁二期项目）**：标段为“高架段无砟轨道设计、供货、安装与调试”，中标企业为印度 `Texmaco Rail & Engineering Ltd.`，合同金额 `INR 1,302,214,433.44`（约 13.02 亿印度卢比）。

2. **《2016–2025 全量中标合同主表》（`List-of-Contract-Awards_2016-2025.xlsx`，共 3,311 条合同记录）**
   亚投行官方汇总的 2016 年至 2025 年底所有主权融资项目（含独立融资与联合融资）及特别基金赠款项目下的**历史中标合同总台账**。全表共 **3,311 条**合同记录，其中项目所属国为印度的合同达 **1,110 条**，中标供应商国籍为印度的合同达 **1,116 条**。

3. **《年度运营采购报告》（2021–2025 共 5 份 PDF）**
   亚投行每年发布的采购统计年报，按借款国和中标企业国籍汇总统计各年度的采购合同数量、金额与占比。

---

### 1.2 《2016–2025 全量中标合同主表》与“采购列表页”的五项核心差别

| 对比维度 | 采购列表页 (`ppo-data-all.js`) | 《2016–2025 全量中标合同主表》 (`.xlsx`) |
| :--- | :--- | :--- |
| **1. 记录阶段与范围** | 包含**采购计划**、**招标公告**、**中标通知**三类日常公告（共 1,189 条，其中中标通知仅 292 条）。 | **仅记录已签署的中标合同**，汇总了全行历史累计 **3,311 条**合同（其中印度项目合同 **1,110 条**）。 |
| **2. 时间跨度** | 主要是近年（尤其 2024–2026 年）在网页滚动发布的公告，早期年份的中标记录在网页列表中不完整；但包含 **2026 年最新中标记录**。 | 完整覆盖 **2016–2025 年** 十年间的历史台账（不含 2026 年新签合同）。 |
| **3. 项目编号关联** | **无项目编号**（仅有项目名称字符串 `pj`，存在拼写微差）。 | **有标准项目编号**（A 列 `Project Number`，如 `P000756`），可与 `01_projects` 精确关联。 |
| **4. 中标企业国籍与采购方式** | 仅有中标企业名称字符串（`cr`），**无中标企业所属国家字段**，也无采购方式、标段类别与银行审查方式。 | **明确记录中标企业所属国家/地区**（M 列 `Origin`），并记录采购类别（工程/货物/咨询）、采购方式（国际招标/国内招标/直接委托）与审查方式（事前/事后）。 |
| **5. 合同金额口径** | 按合同签署时的**原始结算币种**记录（如印度卢比 `INR`、人民币 `CNY`、美元 `USD`），未做统一折算。 | 全部合同金额已由亚投行官方**统一折算为百万美元**（N 列 `Contract Value in USD Million Equivalent`），可直接跨国求和对比。 |

> **使用配合关系**：做 2016–2025 年全量合同统计、跨国金额对比及承包商国籍流向统计时，以 **Excel 主表（3,311 条）** 为主；补充 2026 年最新中标动态、查看正在进行的招标公告与采购计划，或下载单份中标公示 PDF 原件时，使用 **采购列表页（1,189 条）**。

---

### 1.3 官网原始数据接口与页面地址
- **官网导航路径**：顶部菜单 `WORK WITH US` -> `BUSINESS OPPORTUNITIES` -> `Project Procurement Opportunities`
- **项目采购总览页面（含汇总附件下载链接）**
  - 前端展示页面：`https://www.aiib.org/en/opportunities/business/project-procurement/index.html`
  - 中标合同全表 Excel 下载地址：`https://www.aiib.org/en/opportunities/business/project-procurement/_download/List-of-Contract-Awards_2016-2025.xlsx`
  - 年度运营采购报告 PDF 下载地址（2021–2025）：`/en/opportunities/business/project-procurement/_download/2021~2025-AIIB-Annual-Operational-Procurement-Report*.pdf`
- **项目采购公告与合同授予列表数据文件**
  - 前端展示页面：`https://www.aiib.org/en/opportunities/business/project-procurement/list.html`
  - 后台数据接口：`https://www.aiib.org/en/opportunities/business/project-procurement/_common/ppo-data-all.js`
  - 数据格式：JavaScript 变量赋值文本（`var ppoData = [...]`），内部对象的属性键名未加双引号。

### 1.4 采集与落盘流程
- **步骤 1**：请求采购总览页 `project-procurement/index.html`，解析页面内所有 `<a>` 标签，提取中标合同全量 Excel 文件链接与历年《年度运营采购报告》PDF 链接。
- **步骤 2**：请求 `ppo-data-all.js`，通过正则表达式将未加引号的 JavaScript 属性键名（`id`、`cd`、`mb`、`pj`、`ds`、`cr`、`sd`、`pc`、`st`、`ct`、`tp`、`dc`）补全双引号并转换为标准 JSON 数组。
- **步骤 3**：对每条采购记录的发布日期、合同金额与币种（如 `USD`、`INR`、`CNY`、`EUR` 等）、文档相对路径 URL 做结构化拆解。
- **步骤 4**：从全量 1,189 条采购记录中，分别筛选出合同授予子集（`category == "Contract Awards"`，共 292 条）、涉印采购记录子集（`economy` 为 `India` 或 `contractor` 含 `India`，共 272 条）以及涉印合同授予子集（共 42 条），分别保存为独立 JSON 文件。
- **步骤 5**：下载《2016–2025 全量中标合同主表》Excel 文件至 `data/procurement/files/` 目录；当 `--download-pdfs` 设为 `india` 或 `all` 时，一并下载 2021–2025 年 5 份《年度运营采购报告》PDF。

### 1.5 采集命令与参数说明

```bash
# 1. 从头完整复现采集：自动将已有的 procurement 旧数据备份至 data/backups/<时间戳>/，并重新抓取 JSON + Excel + 5 份年度采购报告 PDF（不影响其他模块数据）
uv run python main.py --types procurement --download-pdfs india --mode reset

# 2. 断点续爬模式：当首次运行或上次抓取中途中断时，从断点继续完成采集与附件下载
uv run python main.py --types procurement --download-pdfs india --mode resume

# 3. 仅采集采购列表 JSON + 下载中标合同 Excel（不下载年度采购报告 PDF）
uv run python main.py --types procurement --download-pdfs none --mode reset
```

---

## 二、本地输出文件清单

| 文件路径 | 对应数据源 | 内容说明 | 当前记录条数 / 文件大小 |
| :--- | :--- | :--- | :--- |
| `data/procurement/procurement_all_records.json` | `ppo-data-all.js` | 全行所有采购计划、招标公告与合同授予记录 | 1,189 条 |
| `data/procurement/contract_awards_notices.json` | `ppo-data-all.js` | 从全量记录中筛选出的合同授予通知（`category == "Contract Awards"`） | 292 条 |
| `data/procurement/india_procurement_records.json` | `ppo-data-all.js` | 从全量记录中筛选出的印度项目或印度承包商记录 | 272 条 |
| `data/procurement/india_contract_awards.json` | `ppo-data-all.js` | 涉印记录中的合同授予通知子集 | 42 条 |
| `data/procurement/procurement_overview_files.json` | `project-procurement/index.html` | 中标合同 Excel 与 5 份年度采购报告的原始链接及本地路径索引 | 1 个对象（含 1 个 Excel + 5 个 PDF 索引） |
| `data/procurement/files/List-of-Contract-Awards_2016-2025.xlsx` | 采购总览页附件 | 官方《2016–2025 全量中标合同主表》Excel（含全行 3,311 条合同，其中印度项目 1,110 条） | 3,311 行（127 KB） |
| `data/procurement/files/2021~2025-...-Report.pdf` | 采购总览页附件 | 2021–2025 年共 5 份《年度运营采购报告》PDF | 5 个 PDF 文件 |
| `data/procurement.json` | 同 `procurement_all_records.json` | 模块主汇总文件 | 1,189 条 |

---

## 三、数据表字段说明

### 3.1 采购列表文件字段 (`procurement_all_records.json` 及其子集)
逐一说明 17 个字段的名称、数据类型、对应 `ppo-data-all.js` 中的原始缩写键名及转换规则：
- `record_id`：内部去重键（由序号、发布日期与文档路径拼接）。
- `published_date`（原始键 `id`）：发布日期原始字符串（如 `"Nov 5, 2026"`）。
- `published_year`：从 `published_date` 解析出的四位年份整数。
- `closing_date`（原始键 `cd`）：招标截止日期字符串（仅招标公告类记录有值，其余为空或 `"N/A"`）。
- `economy`（原始键 `mb`）：项目所属成员国名称（如 `"India"`）。
- `project_name`（原始键 `pj`）：关联的项目名称。
- `description`（原始键 `ds`）：合同或招标标段描述。
- `contractor`（原始键 `cr`）：中标承包商或咨询机构名称（仅 `Contract Awards` 类别有值）。
- `signature_date`（原始键 `sd`）：合同签署日期字符串（仅 `Contract Awards` 类别有值）。
- `contract_amount_raw`（原始键 `pc`）：合同金额原始字符串（如 `"INR 2,078,489,885.00"` 或 `"USD 84,000.00"`）。
- `contract_currency`：从 `contract_amount_raw` 提取的三位币种代码（如 `"INR"`、`"USD"`、`"CNY"`）。
- `contract_amount`：从 `contract_amount_raw` 提取的纯数值浮点数。
- `sector`（原始键 `st`）：行业分类（如 `"Energy"`、`"Transport"`、`"Urban"`）。
- `category`（原始键 `ct`）：记录大类（取值包括 `"Contract Awards"`、`"Notices"`、`"Procurement Plan"`）。
- `notice_type`（原始键 `tp`）：具体公告类型（如 `"Contract Award Notice"`、`"Specific Procurement Notice"`、`"General Procurement Notice"`、`"Procurement Plan"`）。
- `document_path`（原始键 `dc`）：关联附件（PDF / Excel / ZIP）的站内相对路径。
- `document_url`：拼接 `https://www.aiib.org` 后的完整附件下载链接。

### 3.2 中标合同全量 Excel 表 (`List-of-Contract-Awards_2016-2025.xlsx`) 表头字段说明
该 Excel 文件包含 1 个工作表（`Sheet1`，共 3,313 行）：第 1 行为统计口径说明，第 2 行为表头（共 16 列，`A` 列至 `P` 列），第 3 至 3,313 行为 3,311 条合同记录。各列表头定义如下：

| 列号 | 原始英文表头 | 字段含义说明 | 样本取值示例 |
| :--- | :--- | :--- | :--- |
| **A 列** | `Project Number` | 亚投行项目编号（以 `P` 开头加 6 位数字，可与 `01_projects` 中的 `project_number` 对应） | `P000756`、`P000379` |
| **B 列** | `AIIB Member` | 项目所属成员国（即借款国） | `India`、`Rwanda`、`China` |
| **C 列** | `Project Name` | 项目英文名称 | `Kochi Metro Rail Project - Phase II` |
| **D 列** | `Sector` | 项目所属行业 | `Transport`、`Energy`、`Water`、`Urban` |
| **E 列** | `Financing Type` | 融资类型（该表主要收录主权项目） | `Sovereign` |
| **F 列** | `Stand-alone/Co-financed` | 独立融资或联合融资标识 | `Stand-alone`、`Co-financing` |
| **G 列** | `Contract Number` | 具体标段的合同编号 | `RW-REG/EDCL-425321-CW-RFP` |
| **H 列** | `Contract Description` | 合同工程、货物或咨询服务的具体内容描述 | `Upgrade of five (5) substations...` |
| **I 列** | `Procurement Category` | 采购标段类别（工程施工 `Works`、货物采购 `Goods`、咨询服务 `Consulting Services`、非咨询服务 `Non-Consulting Services`） | `Works`、`Goods`、`Consulting Services` |
| **J 列** | `Procurement Method` | 采购招标方式（如国际公开竞争招标 `IOCT`、国内公开竞争招标 `NOCT`、直接选聘/直接发包 `Direct Selection` / `Direct Contracting` 等） | `IOCT`、`NOCT`、`Direct Selection` |
| **K 列** | `Bank Review Type` | 亚投行对合同的审查方式（事前审查 `Prior` 或事后抽查 `Post`） | `Prior`、`Post` |
| **L 列** | `Name of the Supplier/Contractor/Consultant` | 中标供应商、承包商或咨询机构名称 | `SHANDONG TAIKAI POWER ENGINEERING CO.,LTD` |
| **M 列** | `Origin of the Supplier/Contractor/Consultant` | **中标企业所属国家/地区**（联合体中标时以 `&` 连接多个国家，如 `India & Korea`） | `India`、`China`、`Germany`、`India & France` |
| **N 列** | `Contract Value in USD Million Equivalent` | 统一折算为**百万美元**的合同金额浮点数 | `9.0963`、`0.2338` |
| **O 列** | `Year of Reporting` | 合同报告年份（四位年份） | `2025`、`2024` |
| **P 列** | `Count Number of Contracts` | 合同计数（每行固定为 `1`，用于透视表求和） | `1` |

---

## 四、数据缺失情况与已知边界
- 在网页版列表 `ppo-data-all.js` 中，当 `category` 为 `"Procurement Plan"` 或 `"Notices"` 时，`contractor`、`signature_date`、`contract_amount_raw` 字段在官网数据源中均为空字符串 `""`；只有当 `category` 为 `"Contract Awards"` 时才包含中标人、签署日期与合同金额。
- 在 `List-of-Contract-Awards_2016-2025.xlsx` 第 1 行说明中，亚投行官方注明该表统计范围为“截至 2025 年底获批的主权融资项目（含独立融资与联合融资）及项目准备特别基金赠款项目”，不包含非主权私营部门项目（`Nonsovereign`）的商业采购合同。
